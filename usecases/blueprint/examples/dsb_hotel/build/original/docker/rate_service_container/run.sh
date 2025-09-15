#!/bin/bash

WORKSPACE_NAME="rate_service_container"
WORKSPACE_DIR=$(pwd)

usage() { 
	echo "Usage: $0 [-h]" 1>&2
	echo "  Required environment variables:"
	
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "    JAEGER_DIAL_ADDR (missing)"
	else
		echo "    JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	if [ -z "${RATE_CACHE_DIAL_ADDR+x}" ]; then
		echo "    RATE_CACHE_DIAL_ADDR (missing)"
	else
		echo "    RATE_CACHE_DIAL_ADDR=$RATE_CACHE_DIAL_ADDR"
	fi
	if [ -z "${RATE_DB_DIAL_ADDR+x}" ]; then
		echo "    RATE_DB_DIAL_ADDR (missing)"
	else
		echo "    RATE_DB_DIAL_ADDR=$RATE_DB_DIAL_ADDR"
	fi
	if [ -z "${RATE_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "    RATE_SERVICE_GRPC_BIND_ADDR (missing)"
	else
		echo "    RATE_SERVICE_GRPC_BIND_ADDR=$RATE_SERVICE_GRPC_BIND_ADDR"
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


rate_service_process() {
	cd $WORKSPACE_DIR
	
	if [ -z "${RATE_CACHE_DIAL_ADDR+x}" ]; then
		if ! rate_cache_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${RATE_DB_DIAL_ADDR+x}" ]; then
		if ! rate_db_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		if ! jaeger_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${RATE_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		if ! rate_service_grpc_bind_addr; then
			return $?
		fi
	fi

	run_rate_service_process() {
		
        cd rate_service_process
        ./rate_service_process --rate_cache.dial_addr=$RATE_CACHE_DIAL_ADDR --rate_db.dial_addr=$RATE_DB_DIAL_ADDR --jaeger.dial_addr=$JAEGER_DIAL_ADDR --rate_service.grpc.bind_addr=$RATE_SERVICE_GRPC_BIND_ADDR &
        RATE_SERVICE_PROCESS=$!
        return $?

	}

	if run_rate_service_process; then
		if [ -z "${RATE_SERVICE_PROCESS+x}" ]; then
			echo "${WORKSPACE_NAME} error starting rate_service_process: function rate_service_process did not set RATE_SERVICE_PROCESS"
			return 1
		else
			echo "${WORKSPACE_NAME} started rate_service_process"
			return 0
		fi
	else
		exitcode=$?
		echo "${WORKSPACE_NAME} aborting rate_service_process due to exitcode ${exitcode} from rate_service_process"
		return $exitcode
	fi
}


run_all() {
	echo "Running rate_service_container"

	# Check that all necessary environment variables are set
	echo "Required environment variables:"
	missing_vars=0
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "  JAEGER_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	
	if [ -z "${RATE_CACHE_DIAL_ADDR+x}" ]; then
		echo "  RATE_CACHE_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RATE_CACHE_DIAL_ADDR=$RATE_CACHE_DIAL_ADDR"
	fi
	
	if [ -z "${RATE_DB_DIAL_ADDR+x}" ]; then
		echo "  RATE_DB_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RATE_DB_DIAL_ADDR=$RATE_DB_DIAL_ADDR"
	fi
	
	if [ -z "${RATE_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "  RATE_SERVICE_GRPC_BIND_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RATE_SERVICE_GRPC_BIND_ADDR=$RATE_SERVICE_GRPC_BIND_ADDR"
	fi
		

	if [ "$missing_vars" -gt 0 ]; then
		echo "Aborting due to missing environment variables"
		return 1
	fi

	rate_service_process
	
	wait
}

run_all
