#!/bin/bash

WORKSPACE_NAME="search_service_container"
WORKSPACE_DIR=$(pwd)

usage() { 
	echo "Usage: $0 [-h]" 1>&2
	echo "  Required environment variables:"
	
	if [ -z "${GEO_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "    GEO_SERVICE_GRPC_DIAL_ADDR (missing)"
	else
		echo "    GEO_SERVICE_GRPC_DIAL_ADDR=$GEO_SERVICE_GRPC_DIAL_ADDR"
	fi
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "    JAEGER_DIAL_ADDR (missing)"
	else
		echo "    JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	if [ -z "${RATE_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "    RATE_SERVICE_GRPC_DIAL_ADDR (missing)"
	else
		echo "    RATE_SERVICE_GRPC_DIAL_ADDR=$RATE_SERVICE_GRPC_DIAL_ADDR"
	fi
	if [ -z "${SEARCH_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "    SEARCH_SERVICE_GRPC_BIND_ADDR (missing)"
	else
		echo "    SEARCH_SERVICE_GRPC_BIND_ADDR=$SEARCH_SERVICE_GRPC_BIND_ADDR"
	fi
		
	exit 1; 
}

while getopts "h" flag; do
	case $flag in
		*)
		usage
		;;
	esac
done


search_service_process() {
	cd $WORKSPACE_DIR
	
	if [ -z "${GEO_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		if ! geo_service_grpc_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		if ! jaeger_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${RATE_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		if ! rate_service_grpc_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${SEARCH_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		if ! search_service_grpc_bind_addr; then
			return $?
		fi
	fi

	run_search_service_process() {
		
        cd search_service_process
        ./search_service_process --geo_service.grpc.dial_addr=$GEO_SERVICE_GRPC_DIAL_ADDR --jaeger.dial_addr=$JAEGER_DIAL_ADDR --rate_service.grpc.dial_addr=$RATE_SERVICE_GRPC_DIAL_ADDR --search_service.grpc.bind_addr=$SEARCH_SERVICE_GRPC_BIND_ADDR &
        SEARCH_SERVICE_PROCESS=$!
        return $?

	}

	if run_search_service_process; then
		if [ -z "${SEARCH_SERVICE_PROCESS+x}" ]; then
			echo "${WORKSPACE_NAME} error starting search_service_process: function search_service_process did not set SEARCH_SERVICE_PROCESS"
			return 1
		else
			echo "${WORKSPACE_NAME} started search_service_process"
			return 0
		fi
	else
		exitcode=$?
		echo "${WORKSPACE_NAME} aborting search_service_process due to exitcode ${exitcode} from search_service_process"
		return $exitcode
	fi
}


run_all() {
	echo "Running search_service_container"

	# Check that all necessary environment variables are set
	echo "Required environment variables:"
	missing_vars=0
	if [ -z "${GEO_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "  GEO_SERVICE_GRPC_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  GEO_SERVICE_GRPC_DIAL_ADDR=$GEO_SERVICE_GRPC_DIAL_ADDR"
	fi
	
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "  JAEGER_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	
	if [ -z "${RATE_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "  RATE_SERVICE_GRPC_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RATE_SERVICE_GRPC_DIAL_ADDR=$RATE_SERVICE_GRPC_DIAL_ADDR"
	fi
	
	if [ -z "${SEARCH_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "  SEARCH_SERVICE_GRPC_BIND_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  SEARCH_SERVICE_GRPC_BIND_ADDR=$SEARCH_SERVICE_GRPC_BIND_ADDR"
	fi
		

	if [ "$missing_vars" -gt 0 ]; then
		echo "Aborting due to missing environment variables"
		return 1
	fi

	search_service_process
	
	wait
}

run_all
