package main

import (
    "encoding/json"
    "flag"
    "fmt"
    "io"
    "io/ioutil"
    "loadgenerator/workload"
    "log"
    "math/rand"
    "net/http"
    "net/url"
    "os"
    "strings"
    "sync"
    "time"
)

type API struct {
    Name     string `json:"name"`
    FuncName string `json:"arg_gen_func_name"`
    Type     string `json:"type"`
}

type Workflow struct {
    Name  string `json:"name"`
    Steps []API  `json:"steps"`
}

type Config struct {
    NumThreads int64      `json:"num_threads"`
    BaseURL    string     `json:"url"`
    Duration   string     `json:"duration"`
    Workflows  []Workflow `json:"workflows"`
    Throughput int64      `json:"tput"`
    IsOriginal bool       `json:"is_original"`
}

type UserState struct {
    UserID     string            `json:"user_id"`
    SessionID  string            `json:"session_id"`
    Username   string            `json:"username"`
    Password   string            `json:"password"`
    CartID     string            `json:"cart_id"`
    AddressIDs []string          `json:"address_ids"`
    CardIDs    []string          `json:"card_ids"`
    CartItems  []string          `json:"cart_items"`
    OrderIDs   []string          `json:"order_ids"`
    IsLoggedIn bool              `json:"is_logged_in"`
    LastItems  []string          `json:"last_items"`
    Metadata   map[string]string `json:"metadata"`
}

func NewUserState(threadID int64) *UserState {
    return &UserState{
        UserID:     generateObjectID(),
        SessionID:  generateObjectID(),
        Username:   fmt.Sprintf("user_%d_%s", threadID, generateObjectID()[:8]),
        Password:   fmt.Sprintf("pass_%s", generateObjectID()[:8]),
        CartID:     generateObjectID(),
        AddressIDs: make([]string, 0),
        CardIDs:    make([]string, 0),
        CartItems:  make([]string, 0),
        OrderIDs:   make([]string, 0),
        IsLoggedIn: false,
        LastItems:  make([]string, 0),
        Metadata:   make(map[string]string),
    }
}

func generateObjectID() string {
    chars := "abcdef0123456789"
    result := ""
    for i := 0; i < 24; i++ {
        result += string(chars[rand.Intn(len(chars))])
    }
    return result
}

type HttpWorkload struct {
    config *Config
}

func NewHttpWorkload(config *Config) *HttpWorkload {
    return &HttpWorkload{config}
}

func (w *HttpWorkload) GetNumThreads() int64 {
    return w.config.NumThreads
}

func (w *HttpWorkload) GetWorkflows() []Workflow {
    return w.config.Workflows
}

func (w *HttpWorkload) GetBaseUrl() string {
    return w.config.BaseURL
}

func (w *HttpWorkload) GetDuration() time.Duration {
    dur, err := time.ParseDuration(w.config.Duration)
    if err != nil {
        log.Fatal(err)
    }
    return dur
}

func (w *HttpWorkload) GetThroughput() int64 {
    return w.config.Throughput
}

type Engine struct {
    Workload   *HttpWorkload
    Stats      []Stat
    Registry   *workload.WorkloadRegistry
    IsOriginal bool
    OutFile    string
}

type Stat struct {
    Start    int64
    Duration int64
    IsError  bool
    Request  RequestInfo
}

type RequestInfo struct {
    Url  string
    Type string
    Fn   func(bool, *UserState) url.Values
}

func PrettyPrintVals(data url.Values) string {
    jsonData, err := json.MarshalIndent(data, "", "  ")
    if err != nil {
        fmt.Println("Error marshalling JSON:", err)
        return ""
    }
    return string(jsonData)
}

func (e *Engine) Run() {
    workflows := e.Workload.GetWorkflows()
    if len(workflows) == 0 {
        log.Fatal("No workflows defined in config")
    }
    
    num_threads := e.Workload.GetNumThreads()
    base_url := e.Workload.GetBaseUrl()
    duration := e.Workload.GetDuration()
    
    var wg sync.WaitGroup
    wg.Add(int(num_threads))
    stat_channel := make(chan Stat, 2*num_threads)
    done := make(chan bool)
    
    go func() {
        count := 0
        for stat := range stat_channel {
            count += 1
            if count%1000 == 0 {
                log.Println("Processed", count, "requests")
            }
            e.Stats = append(e.Stats, stat)
        }
        close(done)
    }()

    // Each thread represents one user
    for i := int64(0); i < num_threads; i++ {
        go func(threadID int64) {
            defer wg.Done()
            client := http.Client{}
            
            // Create user state for this thread/user
            userState := NewUserState(threadID)
            log.Printf("User %d: Created user %s with session %s", threadID, userState.UserID, userState.SessionID)
            
            requestCount := int64(0)
            startTime := time.Now()
            
            // Continue executing workflows until duration expires
            for time.Since(startTime) < duration {
                // Select a random workflow
                workflow := workflows[rand.Intn(len(workflows))]
                log.Printf("User %d: Starting workflow '%s' with %d steps", 
                    threadID, workflow.Name, len(workflow.Steps))
                
                // Execute each step in the workflow
                for stepIndex, api := range workflow.Steps {
                    // Check if duration expired
                    if time.Since(startTime) >= duration {
                        break
                    }
                    
                    target_url := base_url + "/" + api.Name
                    fn := e.Registry.GetGeneratorFunction(api.FuncName)
                    if fn == nil {
                        log.Printf("User %d: No function found for %s", threadID, api.FuncName)
                        continue
                    }
                    
                    // Generate request data with user state (state can be modified by fn)
                    data := fn(e.IsOriginal, userState)
                    
                    // Make request
                    start := time.Now()
                    var resp *http.Response
                    var err error
                    
                    if api.Type == "POST" {
                        resp, err = client.PostForm(target_url, data)
                    } else {
                        encoded_url, err1 := url.Parse(target_url)
                        if err1 != nil {
                            log.Printf("User %d: Failed to parse URL: %v", threadID, err1)
                            continue
                        }
                        encoded_url.RawQuery = data.Encode()
                        log.Printf("User %d: Step %d/%d - Making %s request to %s", 
                            threadID, stepIndex+1, len(workflow.Steps), api.Type, encoded_url.String())
                        resp, err = client.Get(encoded_url.String())
                    }
                    
                    duration := time.Since(start)
                    var stat Stat
                    stat.Start = start.UnixNano()
                    stat.Duration = duration.Nanoseconds()
                    stat.Request = RequestInfo{Url: target_url, Type: api.Type, Fn: fn}
                    
                    if err != nil {
                        log.Printf("User %d: Request error: %v", threadID, err)
                        stat.IsError = true
                    } else {
                        statusOK := resp.StatusCode >= 200 && resp.StatusCode < 300
                        if !statusOK {
                            stat.IsError = true
                            bytes, _ := io.ReadAll(resp.Body)
                            log.Printf("User %d: HTTP error %s: %s", threadID, resp.Status, string(bytes))
                        }
                    }
                    
                    if resp != nil {
                        io.Copy(ioutil.Discard, resp.Body)
                        resp.Body.Close()
                    }
                    
                    stat_channel <- stat
                    requestCount++
                    
                    // Add delay between steps in workflow
                    time.Sleep(time.Duration(rand.Intn(500)+100) * time.Millisecond)
                }
                
                log.Printf("User %d: Completed workflow '%s', total requests: %d", 
                    threadID, workflow.Name, requestCount)
                
                // Add delay between workflows
                time.Sleep(time.Duration(rand.Intn(2000)+500) * time.Millisecond)
            }
            
            log.Printf("User %d: Finished after %v with %d total requests", 
                threadID, time.Since(startTime), requestCount)
        }(i)
    }
    
    wg.Wait()
    close(stat_channel)
    <-done
    log.Println("Finished all requests")
}

func (e *Engine) PrintStats() {
    var num_errors int64
    var num_reqs int64
    var sum_durations int64
    stat_strings := []string{}
    for _, stat := range e.Stats {
        num_reqs += 1
        if stat.IsError {
            num_errors += 1
        }
        sum_durations += stat.Duration
        stat_strings = append(stat_strings, fmt.Sprintf("%s,%d,%d,%t", stat.Request.Url, stat.Start, stat.Duration, stat.IsError))
    }

    fmt.Println("Total Number of Requests:", num_reqs)
    fmt.Println("Successful Requests:", num_reqs-num_errors)
    fmt.Println("Error Responses:", num_errors)
    fmt.Println("Average Latency:", float64(sum_durations)/float64(num_reqs))
    
    // Write to file
    header := "Name,Start,Duration,IsError\n"
    data := header + strings.Join(stat_strings, "\n")
    f, err := os.OpenFile(e.OutFile, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0755)
    if err != nil {
        log.Fatal(err)
    }
    defer f.Close()
    _, err = f.WriteString(data)
    if err != nil {
        log.Fatal(err)
    }
}

func main() {
    configPtr := flag.String("config", "", "Path to the configuration file")
    outfilePtr := flag.String("outfile", "latency.csv", "File to which the request data will be written")
    flag.Parse()

    configFile := *configPtr
    if configFile == "" {
        log.Fatal("Usage: go run main.go -config=<path to config.json>")
    }

    file, err := os.Open(configFile)
    if err != nil {
        log.Fatal(err)
    }
    defer file.Close()
    bytes, err := ioutil.ReadAll(file)
    if err != nil {
        log.Fatal(err)
    }
    var config Config
    err = json.Unmarshal(bytes, &config)
    if err != nil {
        log.Fatal(err)
    }
    
    workload_conf := NewHttpWorkload(&config)
    engine := &Engine{Workload: workload_conf, Registry: workload.NewWorkloadRegistry(), IsOriginal: config.IsOriginal, OutFile: *outfilePtr}
    
    log.Println("Running workflow-based load generation")
    log.Println("Number of users (threads):", config.NumThreads)
    log.Println("Duration:", config.Duration)
    log.Println("Output file:", *outfilePtr)
    
    engine.Run()
    engine.PrintStats()
}