## Workload generator

Workload generator (taken from blueprint-compiler GitLab) that generates HTTP workload for the applications.

### Usage

Once you have deployed the application, use the following:

```
> cd ./wrk_http
> go build
> ./wrk_http -config=path/to/config.json -tput=10000 -duration=1m -outfile=stats.csv
```

You can check an example of configuration file in `apps/dsb_hotel/workload/workloadgen/config.json`.

### Command Line Options


- config: Path to config file describing the list of APIs and their respective request parameter generation functions

- tput: Desired throughput (in reqs/s)

- duration: Duration for which the workload should execute. Must be a valid Go time string

- outfile: Path to file where the measured statistics will be written.


### Config Options

The config file consists of the following 2 options

- `url`: Full url where the front-end web-server is hosted
- `apis`: List of all APIs that need to be executed

Each API must have the following fields

- `name`: The name of the endpoint
- `arg_gen_func_name`: The name of the function ued to generate the request parameters
- `proportion`: The percentage of all requests that should be for this API. This value should be an integer between 0 and 100.
- `type`: Type of the request. One of POST or GET.

Note that the sum of all proportions for APIs should be exactly 100