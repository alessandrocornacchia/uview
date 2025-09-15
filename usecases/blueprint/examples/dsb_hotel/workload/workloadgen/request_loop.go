package workloadgen

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	//"gitlab.mpi-sws.org/cld/blueprint/blueprint-compiler/workload"

	rand2 "golang.org/x/exp/rand"
	"gonum.org/v1/gonum/stat/distuv"
)

// type API struct {
// 	Name string `json:"name"`
// 	//FuncName   string `json:"arg_gen_func_name"`
// 	Proportion int64  `json:"proportion"` // Proportion of the workload that should be this request. Sum of proportions for all APIs should be equal to 100.
// 	Type       string `json:"type"`       // Type can only be GET or POST. For Millenial generated APIs, the type is always POST.
// }

type Config struct {
	NumThreads int64 `json:"num_threads"`
	//BaseURL    string `json:"url"`
	NumReqs  int64  `json:"num_reqs"` // Total number of requests
	Duration string `json:"duration"`
	//APIs       []API  `json:"apis"`
	Throughput int64 `json:"tput"` // Number of requests to be sent per second
}

type WorkloadConfig struct {
	config *Config
}

func NewWorkloadConfig(config *Config) *WorkloadConfig {
	return &WorkloadConfig{config}
}

func (w *WorkloadConfig) GetNumThreads() int64 {
	return w.config.NumThreads
}

func (w *WorkloadConfig) GetMaxRequests() int64 {
	return w.config.NumReqs
}

// func (w *HttpWorkload) GetAPIs() []API {
// 	return w.config.APIs
// }

// func (w *HttpWorkload) GetBaseUrl() string {
// 	return w.config.BaseURL
// }

func (w *WorkloadConfig) GetDuration() time.Duration {
	dur, err := time.ParseDuration(w.config.Duration)
	if err != nil {
		log.Fatal(err)
	}
	return dur
}

func (w *WorkloadConfig) GetThroughput() int64 {
	return w.config.Throughput
}

type Stat struct {
	Start    int64
	Duration int64
	IsError  bool
}

// concrete implementation of the RunRequest method is deferred to
// the specific Blueprint applications
type RequestRunner interface {
	RunRequest(ctx context.Context, stat_channel chan Stat)
}

type Engine struct {
	Workload *WorkloadConfig
	Stats    []Stat
	//Registry   *workload.WorkloadRegistry
	IsOriginal     bool
	OutFile        string
	WorkloadRunner RequestRunner
}

// type RequestInfo struct {
// 	Url  string
// 	Type string
// 	Fn   func(bool) url.Values
// }

/*
here is the main loop generating the various go routines to make requests,
at the target throughput, and collect the stats.
*/
func (e *Engine) RunOpenLoop(ctx context.Context) {
	//apis := e.Workload.GetAPIs()
	duration := e.Workload.GetDuration()
	target_tput := e.Workload.GetThroughput()
	log.Println("Target throughput", target_tput)
	log.Println("Target duration", duration)

	// --
	// this part is about generating requests for multiple API endpoints with
	// different propoprtions of client requests. Need however to change this
	// to make compatile with blueprint abstraction and not assume HTTP endpoints
	// --

	// request_infos := make(map[string]RequestInfo)
	// sort.Slice(apis, func(i, j int) bool { return apis[i].Proportion > apis[j].Proportion })
	// proportion_map := make(map[int64]string)
	// var last_proportion_val int64
	// for _, api := range apis {
	// 	target_url := base_url + "/" + api.Name
	// 	requestInfo := RequestInfo{Url: target_url, Type: api.Type, Fn: e.Registry.GetGeneratorFunction(api.FuncName)}
	// 	request_infos[api.Name] = requestInfo
	// 	var i int64
	// 	for i = 0; i < api.Proportion; i += 1 {
	// 		proportion_map[last_proportion_val+i] = api.Name
	// 	}
	// 	last_proportion_val += i
	// }

	// Launch stat collector channel
	stat_channel := make(chan Stat, target_tput)
	done := make(chan bool)
	go func() {
		count := 0
		// this ranges over event queued in this channel
		for stat := range stat_channel {
			count += 1
			if count%1000 == 0 {
				log.Println("Processed", count, "requests")
			}
			e.Stats = append(e.Stats, stat)
		}
		close(done)
	}()

	tick_every := float64(1e9) / float64(target_tput)
	tick_val := time.Duration(int64(1e9 / target_tput))
	log.Println("Ticking after every", tick_val)
	stop := make(chan bool)
	var wg sync.WaitGroup
	var i = 0
	// Launch the request maker goroutine that launches a request every tick_val
	go func() {
		src := rand2.NewSource(0)
		g := distuv.Poisson{Lambda: 100, Src: src}
		timer := time.NewTimer(0 * time.Second)
		next := time.Now()
		for {
			select {
			case <-stop:
				return
			case <-ctx.Done():
				return // TODO does this make sense?
			case <-timer.C:
				// Select a request based on proportions
				//num := int64(rand.Intn(100))
				//api_name := proportion_map[num]
				//requestInfo := request_infos[api_name]
				wg.Add(1)
				i += 1
				// every client request has its own go routine...
				// not very efficient
				go func() {
					// this posts a done message when the go routine ends
					defer wg.Done()
					e.WorkloadRunner.RunRequest(ctx, stat_channel)
				}()
				next = next.Add(time.Duration(g.Rand()*tick_every/100) * time.Nanosecond)
				waitt := next.Sub(time.Now())
				timer.Reset(waitt)
			}
		}
	}()

	// Let the requests happen for the desired duration
	// ... here execution continues, and sleeps....

	time.Sleep(duration)
	stop <- true
	wg.Wait()
	log.Println("Total launched routines:", i)
	close(stat_channel)
	<-done
	log.Println("Finished all requests")
}

func (e *Engine) RunWithThreadPool(ctx context.Context) {
	num_threads := e.Workload.GetNumThreads()
	max_reqs := e.Workload.GetMaxRequests()
	target_tput := e.Workload.GetThroughput() / num_threads
	duration := e.Workload.GetDuration()
	log.Println("Target throughput", target_tput)
	log.Println("Experiment duration", duration)

	var curReqs, i int64
	var wg sync.WaitGroup

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

	tick_every := float64(1e9) / float64(target_tput)
	tick_val := time.Duration(int64(1e9 / target_tput))
	log.Println("Ticking after every", tick_val)
	//stop := make(chan bool, num_threads)

	threadctx, cancel := context.WithCancel(context.Background())
	wg.Add(int(num_threads))
	// generate the threads
	for i = 0; i < num_threads; i++ {
		go func() {
			defer wg.Done()
			src := rand2.NewSource(0)
			g := distuv.Poisson{Lambda: 100, Src: src}
			timer := time.NewTimer(0 * time.Second)
			next := time.Now()
			for curReqs < max_reqs { // until we don't hit the maximum
				select {
				case <-threadctx.Done(): // this happens after duration seconds
					fmt.Println("Experiment duration reached. Terminating routine")
					return
				case <-ctx.Done():
					return // Blueprint context Done
				case <-timer.C:
					// Select a request based on proportions
					//num := int64(rand.Intn(100))
					//api_name := proportion_map[num]
					//requestInfo := request_infos[api_name]

					e.WorkloadRunner.RunRequest(ctx, stat_channel)
					next = next.Add(time.Duration(g.Rand()*tick_every/100) * time.Nanosecond)
					waitt := next.Sub(time.Now())
					timer.Reset(waitt)

					atomic.AddInt64(&curReqs, 1)
				}
			}
		}()
	}
	// Let the requests happen for the desired duration
	// ... here execution continues, and sleeps....

	time.Sleep(duration)
	cancel()  // cancel the context for the various threads
	wg.Wait() // wait for them to return
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
		stat_strings = append(stat_strings, fmt.Sprintf("%d,%d,%t", stat.Start, stat.Duration, stat.IsError))
	}

	fmt.Println("Total Number of Requests:", num_reqs)
	fmt.Println("Successful Requests:", num_reqs-num_errors)
	fmt.Println("Error Responses:", num_errors)
	fmt.Println("Average Latency:", float64(sum_durations)/float64(num_reqs))
	// Write to file
	header := "Start,Duration,IsError\n"
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
	fmt.Println("Stats written to:", e.OutFile)
}
