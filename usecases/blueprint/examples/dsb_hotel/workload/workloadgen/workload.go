package workloadgen

import (
	"context"
	"encoding/json"
	"flag"
	"io/ioutil"
	"log"
	"os"
	"time"

	"github.com/blueprint-uservices/blueprint/examples/dsb_hotel/workflow/hotelreservation"
)

type SimpleWorkload interface {
	ImplementsSimpleWorkload(ctx context.Context) error
}

type workloadGen struct {
	SimpleWorkload

	frontend hotelreservation.FrontEndService
}

func NewSimpleWorkload(ctx context.Context, frontend hotelreservation.FrontEndService) (SimpleWorkload, error) {
	return &workloadGen{frontend: frontend}, nil
}

func (s *workloadGen) ImplementsSimpleWorkload(context.Context) error {
	return nil
}

// concrete implementation of the request runner interface within the engine.
type DsbHotelRequestRunner struct {
	workloadGen *workloadGen
}

// implements request_loop.RequestRunner interface
// ( this is called inside the RunOpenLoop method of the Engine )
func (dbhrr *DsbHotelRequestRunner) RunRequest(ctx context.Context, stat_channel chan Stat) {
	start := time.Now()
	var stat Stat
	stat.Start = start.UnixNano() // start time measurement

	var err error

	// list of requests handlers taken from the test directory of dsb_hotel
	_, err = dbhrr.workloadGen.frontend.SearchHandler(ctx, "Vaastav", "2015-04-09", "2015-04-10", 37.7835, -122.41, "en")
	// _, err = dbhrr.workloadGen.frontend.UserHandler(ctx, "Cornell_1", "1111111111")
	// _, err = dbhrr.workloadGen.frontend.RecommendHandler(ctx, 37.7835, -122.41, "dis", "en")
	// _, err = dbhrr.workloadGen.frontend.ReservationHandler(ctx, "2015-04-09", "2015-04-10", "1", "Cornell User 1", "Cornell_1", "1111111111", 1)

	stat.Duration = time.Since(start).Nanoseconds()
	if err != nil {
		// looks like this contains the error message e.g., Status Code is 500
		// but need to check better
		log.Println(err)
		stat.IsError = true
	} /*else {
		// print only when successful
		fmt.Println("Query found", len(hotels), "hotels!")
	}*/
	stat_channel <- stat
}

var configPtr = flag.String("config", "", "Path to the configuration file")
var tputPtr = flag.Int("tput", 0, "Desired throughput")
var durationPtr = flag.String("duration", "", "Duration for which the workload should run")
var outfilePtr = flag.String("outfile", "latency.csv", "File to which the request data will be written")
var modePtr = flag.String("mode", "pool", "Generation mode: pool or openloop")

// --- Entrypoint for the workload generator
// Blueprint:
// " the logic of the workload generator should reside in the Run method"
// https://github.com/Blueprint-uServices/blueprint/tree/main/plugins/workload
// --
func (s *workloadGen) Run(ctx context.Context) error {

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
	// use command line arguments if provided (take over the json file)
	if *tputPtr != 0 {
		config.Throughput = int64(*tputPtr)
	}
	if *durationPtr != "" {
		config.Duration = *durationPtr
	}
	workload_conf := NewWorkloadConfig(&config)

	wload_runner := &DsbHotelRequestRunner{workloadGen: s}
	engine := &Engine{Workload: workload_conf, WorkloadRunner: wload_runner, OutFile: *outfilePtr}

	if *modePtr == "openloop" {
		engine.RunOpenLoop(ctx)
	} else if *modePtr == "pool" {
		engine.RunWithThreadPool(ctx)
	}

	engine.PrintStats()

	// function must return, at this point we completed so we return without
	// errors
	return nil
}
