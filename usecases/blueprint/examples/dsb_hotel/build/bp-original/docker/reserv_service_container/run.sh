#!/bin/bash

WORKSPACE_NAME="reserv_service_container"
WORKSPACE_DIR=$(pwd)

usage() { 
	echo "Usage: $0 [-h]" 1>&2
	echo "  Required environment variables:"
	
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "    JAEGER_DIAL_ADDR (missing)"
	else
		echo "    JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	if [ -z "${RESERV_CACHE_DIAL_ADDR+x}" ]; then
		echo "    RESERV_CACHE_DIAL_ADDR (missing)"
	else
		echo "    RESERV_CACHE_DIAL_ADDR=$RESERV_CACHE_DIAL_ADDR"
	fi
	if [ -z "${RESERV_DB_DIAL_ADDR+x}" ]; then
		echo "    RESERV_DB_DIAL_ADDR (missing)"
	else
		echo "    RESERV_DB_DIAL_ADDR=$RESERV_DB_DIAL_ADDR"
	fi
	if [ -z "${RESERV_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "    RESERV_SERVICE_GRPC_BIND_ADDR (missing)"
	else
		echo "    RESERV_SERVICE_GRPC_BIND_ADDR=$RESERV_SERVICE_GRPC_BIND_ADDR"
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


reserv_service_process() {
	cd $WORKSPACE_DIR
	
	if [ -z "${RESERV_CACHE_DIAL_ADDR+x}" ]; then
		if ! reserv_cache_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${RESERV_DB_DIAL_ADDR+x}" ]; then
		if ! reserv_db_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		if ! jaeger_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${RESERV_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		if ! reserv_service_grpc_bind_addr; then
			return $?
		fi
	fi

	run_reserv_service_process() {
		
        cd reserv_service_process
        ./reserv_service_process --reserv_cache.dial_addr=$RESERV_CACHE_DIAL_ADDR --reserv_db.dial_addr=$RESERV_DB_DIAL_ADDR --jaeger.dial_addr=$JAEGER_DIAL_ADDR --reserv_service.grpc.bind_addr=$RESERV_SERVICE_GRPC_BIND_ADDR &
        RESERV_SERVICE_PROCESS=$!
        return $?

	}

	if run_reserv_service_process; then
		if [ -z "${RESERV_SERVICE_PROCESS+x}" ]; then
			echo "${WORKSPACE_NAME} error starting reserv_service_process: function reserv_service_process did not set RESERV_SERVICE_PROCESS"
			return 1
		else
			echo "${WORKSPACE_NAME} started reserv_service_process"
			return 0
		fi
	else
		exitcode=$?
		echo "${WORKSPACE_NAME} aborting reserv_service_process due to exitcode ${exitcode} from reserv_service_process"
		return $exitcode
	fi
}


run_all() {
	echo "Running reserv_service_container"

	# Check that all necessary environment variables are set
	echo "Required environment variables:"
	missing_vars=0
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "  JAEGER_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	
	if [ -z "${RESERV_CACHE_DIAL_ADDR+x}" ]; then
		echo "  RESERV_CACHE_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RESERV_CACHE_DIAL_ADDR=$RESERV_CACHE_DIAL_ADDR"
	fi
	
	if [ -z "${RESERV_DB_DIAL_ADDR+x}" ]; then
		echo "  RESERV_DB_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RESERV_DB_DIAL_ADDR=$RESERV_DB_DIAL_ADDR"
	fi
	
	if [ -z "${RESERV_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "  RESERV_SERVICE_GRPC_BIND_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RESERV_SERVICE_GRPC_BIND_ADDR=$RESERV_SERVICE_GRPC_BIND_ADDR"
	fi
		

	if [ "$missing_vars" -gt 0 ]; then
		echo "Aborting due to missing environment variables"
		return 1
	fi

	reserv_service_process
	
	wait
}

run_all
