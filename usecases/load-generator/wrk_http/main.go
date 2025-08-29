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
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	rand2 "golang.org/x/exp/rand"
	"gonum.org/v1/gonum/stat/distuv"
)

type API struct {
	Name       string `json:"name"`
	FuncName   string `json:"arg_gen_func_name"`
	Proportion int64  `json:"proportion"` // Proportion of the workload that should be this request. Sum of proportions for all APIs should be equal to 100.
	Type       string `json:"type"`       // Type can only be GET or POST. For Millenial generated APIs, the type is always POST.
}

type Config struct {
	NumThreads int64  `json:"num_threads"`
	BaseURL    string `json:"url"`
	NumReqs    int64  `json:"num_reqs,omitempty"` // Total number of requests (optional)
	Duration   string `json:"duration"`
	APIs       []API  `json:"apis"`
	Throughput int64  `json:"tput"` // Number of requests to be sent per second
	IsOriginal bool   `json:"is_original"`
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

func (w *HttpWorkload) GetMaxRequests() int64 {
	return w.config.NumReqs
}

func (w *HttpWorkload) GetAPIs() []API {
	return w.config.APIs
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
	Fn   func(bool) url.Values
}

func PrettyPrintVals(data url.Values) string {
	// Marshal the map into pretty-printed JSON
	jsonData, err := json.MarshalIndent(data, "", "  ") // "" for prefix, "  " for indentation
	if err != nil {
		fmt.Println("Error marshalling JSON:", err)
		return ""
	}
	return string(jsonData)
}

func (e *Engine) RunRequest(client *http.Client, req *RequestInfo, stat_channel chan Stat) {
	start := time.Now()
	var resp *http.Response
	var err error
	vals := req.Fn(e.IsOriginal)
	
	
	// log request details
	log.Println("Making request to", req.Url, "with args", PrettyPrintVals(vals))
	
	// Make request
	if req.Type == "POST" {
		resp, err = client.PostForm(req.Url, vals)
	} else if req.Type == "GET" {
		encoded_url, err1 := url.Parse(req.Url)
		if err1 != nil {
			log.Fatal("Failed to parse URL")
		}
		encoded_url.RawQuery = vals.Encode()
		resp, err = client.Get(encoded_url.String())
	}
	var stat Stat
	stat.Request = *req
	stat.Start = start.UnixNano()
	stat.Duration = time.Since(start).Nanoseconds()
	if err != nil {
		log.Println(err)
		stat.IsError = true
	}
	statusOK := resp.StatusCode >= 200 && resp.StatusCode < 300
	if !statusOK {
		stat.IsError = true
		bytes, _ := io.ReadAll(resp.Body)
		log.Println(resp.Status+",", string(bytes))
	}
	io.Copy(ioutil.Discard, resp.Body)
	resp.Body.Close()
	stat_channel <- stat
}

func (e *Engine) RunOpenLoop() {
	apis := e.Workload.GetAPIs()
	duration := e.Workload.GetDuration()
	base_url := e.Workload.GetBaseUrl()
	target_tput := e.Workload.GetThroughput()
	log.Println("Target throughput", target_tput)
	request_infos := make(map[string]RequestInfo)
	sort.Slice(apis, func(i, j int) bool { return apis[i].Proportion > apis[j].Proportion })
	proportion_map := make(map[int64]string)
	var last_proportion_val int64
	for _, api := range apis {
		target_url := base_url + "/" + api.Name
		requestInfo := RequestInfo{Url: target_url, Type: api.Type, Fn: e.Registry.GetGeneratorFunction(api.FuncName)}
		request_infos[api.Name] = requestInfo
		var i int64
		for i = 0; i < api.Proportion; i += 1 {
			proportion_map[last_proportion_val+i] = api.Name
		}
		last_proportion_val += i
	}
	// Launch stat collector channel
	stat_channel := make(chan Stat, target_tput)
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
	defaultRoundTripper := http.DefaultTransport
	defaultTransportPointer, ok := defaultRoundTripper.(*http.Transport)
	if !ok {
		panic(fmt.Sprintf("defaultRoundTripper not an *http.Transport"))
	}
	defaultTransport := *defaultTransportPointer // dereference it to get a copy of the struct that the pointer points to
	defaultTransport.MaxIdleConns = 60000
	defaultTransport.MaxIdleConnsPerHost = 60000
	defaultTransport.MaxConnsPerHost = 10000
	client := &http.Client{Transport: &defaultTransport}

	// Launch the request maker goroutine that launches a request every tick_val
	tick_every := float64(1e9) / float64(target_tput)
	tick_val := time.Duration(int64(1e9 / target_tput))
	log.Println("Ticking after every", tick_val)
	//ticker := time.NewTicker(tick_val * time.Nanosecond)
	stop := make(chan bool)
	var wg sync.WaitGroup
	var i int64
	// go func() {
	// 	for {
	// 		select {
	// 		case <-stop:
	// 			return
	// 		case <-ticker.C:
	// 			// Select a request based on proportions
	// 			num := int64(rand.Intn(100))
	// 			api_name := proportion_map[num]
	// 			requestInfo := request_infos[api_name]
	// 			wg.Add(1)
	// 			i += 1
	// 			go func() {
	// 				defer wg.Done()
	// 				e.RunRequest(client, &requestInfo, stat_channel)
	// 			}()
	// 		}
	// 	}
	// }()
	go func() {
		src := rand2.NewSource(0)
		g := distuv.Poisson{100, src}
		timer := time.NewTimer(0 * time.Second)
		next := time.Now()
		for {
			select {
			case <-stop:
				return
			case <-timer.C:
				// Select a request based on proportions
				num := int64(rand.Intn(100))
				api_name := proportion_map[num]
				requestInfo := request_infos[api_name]
				wg.Add(1)
				go func() {
					defer wg.Done()
					e.RunRequest(client, &requestInfo, stat_channel)
				}()
				next = next.Add(time.Duration(g.Rand()*tick_every/100) * time.Nanosecond)
				waitt := next.Sub(time.Now())
				timer.Reset(waitt)
			}
		}
	}()
	// Let the requests happen for the desired duration
	time.Sleep(duration)
	stop <- true
	wg.Wait()
	log.Println("Total launched routines:", i)
	close(stat_channel)
	<-done
	log.Println("Finished all requests")
}


func (e *Engine) Run() {
	// right now supports only one API
	api := e.Workload.GetAPIs()[0]
	num_threads := e.Workload.GetNumThreads()
	max_reqs := e.Workload.GetMaxRequests()
	base_url := e.Workload.GetBaseUrl()
	target_url := base_url + "/" + api.Name
	fn := e.Registry.GetGeneratorFunction(api.FuncName)
	data := fn(e.IsOriginal)
	var curReqs, i int64
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
	for i = 0; i < num_threads; i++ {
		go func() {
			// this is one user
			defer wg.Done()
			client := http.Client{}
			for curReqs < max_reqs {
				
				encoded_url, err1 := url.Parse(target_url)
				if err1 != nil {
					log.Fatal("Failed to parse URL")
				}
				encoded_url.RawQuery = data.Encode()
				// Make request
				start := time.Now()
				// resp, err := client.PostForm(target_url, data)
				// HTTP GET
				log.Println("Making GET request to", encoded_url.String())
				resp, err := client.Get(encoded_url.String())
				
				duration := time.Since(start)
				var stat Stat
				stat.Start = start.UnixNano()
				stat.Duration = duration.Nanoseconds()
				if err != nil {
					log.Println(resp.Status, err)
					stat.IsError = true
				}
				// print response when success
				if !stat.IsError {
					bytes, err := io.ReadAll(resp.Body)
					if err != nil {
						log.Println("Error reading response body:", err)
					} else {
						log.Println("Response:", string(bytes))
					}
				}

				io.Copy(ioutil.Discard, resp.Body)
				resp.Body.Close()
				stat_channel <- stat
				atomic.AddInt64(&curReqs, 1)
			}
		}()
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
	tputPtr := flag.Int("tput", 0, "Desired throughput")
	durationPtr := flag.String("duration", "", "Duration for which the workload should run")
	outfilePtr := flag.String("outfile", "latency.csv", "File to which the request data will be written")
	flag.Parse()

	configFile := *configPtr
	if configFile == "" {
		log.Fatal("Usage: go run main.go -config=<path to config.json> -tput=<desired_tput>")
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
	if *tputPtr != 0 {
		config.Throughput = int64(*tputPtr)
	}
	if *durationPtr != "" {
		config.Duration = *durationPtr
	}
	workload_conf := NewHttpWorkload(&config)
	engine := &Engine{Workload: workload_conf, Registry: workload.NewWorkloadRegistry(), IsOriginal: config.IsOriginal, OutFile: *outfilePtr}
	// if NumReqs is specified, run closed loop
	if config.NumReqs != 0 {
		log.Println("Running closed loop with", config.NumReqs, "requests")
		engine.Run()
	} else {
		log.Println("Running open loop for", config.Duration)
		log.Println("Target throughput", config.Throughput)
		log.Println("Output file", *outfilePtr)

		engine.RunOpenLoop()
	}
	engine.PrintStats()
}
