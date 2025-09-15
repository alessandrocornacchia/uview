#!/bin/bash

WORKSPACE_NAME="profile_service_container"
WORKSPACE_DIR=$(pwd)

usage() { 
	echo "Usage: $0 [-h]" 1>&2
	echo "  Required environment variables:"
	
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "    JAEGER_DIAL_ADDR (missing)"
	else
		echo "    JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	if [ -z "${PROFILE_CACHE_DIAL_ADDR+x}" ]; then
		echo "    PROFILE_CACHE_DIAL_ADDR (missing)"
	else
		echo "    PROFILE_CACHE_DIAL_ADDR=$PROFILE_CACHE_DIAL_ADDR"
	fi
	if [ -z "${PROFILE_DB_DIAL_ADDR+x}" ]; then
		echo "    PROFILE_DB_DIAL_ADDR (missing)"
	else
		echo "    PROFILE_DB_DIAL_ADDR=$PROFILE_DB_DIAL_ADDR"
	fi
	if [ -z "${PROFILE_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "    PROFILE_SERVICE_GRPC_BIND_ADDR (missing)"
	else
		echo "    PROFILE_SERVICE_GRPC_BIND_ADDR=$PROFILE_SERVICE_GRPC_BIND_ADDR"
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


profile_service_process() {
	cd $WORKSPACE_DIR
	
	if [ -z "${PROFILE_CACHE_DIAL_ADDR+x}" ]; then
		if ! profile_cache_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${PROFILE_DB_DIAL_ADDR+x}" ]; then
		if ! profile_db_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		if ! jaeger_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${PROFILE_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		if ! profile_service_grpc_bind_addr; then
			return $?
		fi
	fi

	run_profile_service_process() {
		
        cd profile_service_process
        ./profile_service_process --profile_cache.dial_addr=$PROFILE_CACHE_DIAL_ADDR --profile_db.dial_addr=$PROFILE_DB_DIAL_ADDR --jaeger.dial_addr=$JAEGER_DIAL_ADDR --profile_service.grpc.bind_addr=$PROFILE_SERVICE_GRPC_BIND_ADDR &
        PROFILE_SERVICE_PROCESS=$!
        return $?

	}

	if run_profile_service_process; then
		if [ -z "${PROFILE_SERVICE_PROCESS+x}" ]; then
			echo "${WORKSPACE_NAME} error starting profile_service_process: function profile_service_process did not set PROFILE_SERVICE_PROCESS"
			return 1
		else
			echo "${WORKSPACE_NAME} started profile_service_process"
			return 0
		fi
	else
		exitcode=$?
		echo "${WORKSPACE_NAME} aborting profile_service_process due to exitcode ${exitcode} from profile_service_process"
		return $exitcode
	fi
}


run_all() {
	echo "Running profile_service_container"

	# Check that all necessary environment variables are set
	echo "Required environment variables:"
	missing_vars=0
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "  JAEGER_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	
	if [ -z "${PROFILE_CACHE_DIAL_ADDR+x}" ]; then
		echo "  PROFILE_CACHE_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  PROFILE_CACHE_DIAL_ADDR=$PROFILE_CACHE_DIAL_ADDR"
	fi
	
	if [ -z "${PROFILE_DB_DIAL_ADDR+x}" ]; then
		echo "  PROFILE_DB_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  PROFILE_DB_DIAL_ADDR=$PROFILE_DB_DIAL_ADDR"
	fi
	
	if [ -z "${PROFILE_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "  PROFILE_SERVICE_GRPC_BIND_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  PROFILE_SERVICE_GRPC_BIND_ADDR=$PROFILE_SERVICE_GRPC_BIND_ADDR"
	fi
		

	if [ "$missing_vars" -gt 0 ]; then
		echo "Aborting due to missing environment variables"
		return 1
	fi

	profile_service_process
	
	wait
}

run_all
