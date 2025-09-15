#!/bin/bash

WORKSPACE_NAME="geo_service_container"
WORKSPACE_DIR=$(pwd)

usage() { 
	echo "Usage: $0 [-h]" 1>&2
	echo "  Required environment variables:"
	
	if [ -z "${GEO_DB_DIAL_ADDR+x}" ]; then
		echo "    GEO_DB_DIAL_ADDR (missing)"
	else
		echo "    GEO_DB_DIAL_ADDR=$GEO_DB_DIAL_ADDR"
	fi
	if [ -z "${GEO_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "    GEO_SERVICE_GRPC_BIND_ADDR (missing)"
	else
		echo "    GEO_SERVICE_GRPC_BIND_ADDR=$GEO_SERVICE_GRPC_BIND_ADDR"
	fi
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "    JAEGER_DIAL_ADDR (missing)"
	else
		echo "    JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
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


geo_service_process() {
	cd $WORKSPACE_DIR
	
	if [ -z "${GEO_DB_DIAL_ADDR+x}" ]; then
		if ! geo_db_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		if ! jaeger_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${GEO_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		if ! geo_service_grpc_bind_addr; then
			return $?
		fi
	fi

	run_geo_service_process() {
		
        cd geo_service_process
        ./geo_service_process --geo_db.dial_addr=$GEO_DB_DIAL_ADDR --jaeger.dial_addr=$JAEGER_DIAL_ADDR --geo_service.grpc.bind_addr=$GEO_SERVICE_GRPC_BIND_ADDR &
        GEO_SERVICE_PROCESS=$!
        return $?

	}

	if run_geo_service_process; then
		if [ -z "${GEO_SERVICE_PROCESS+x}" ]; then
			echo "${WORKSPACE_NAME} error starting geo_service_process: function geo_service_process did not set GEO_SERVICE_PROCESS"
			return 1
		else
			echo "${WORKSPACE_NAME} started geo_service_process"
			return 0
		fi
	else
		exitcode=$?
		echo "${WORKSPACE_NAME} aborting geo_service_process due to exitcode ${exitcode} from geo_service_process"
		return $exitcode
	fi
}


run_all() {
	echo "Running geo_service_container"

	# Check that all necessary environment variables are set
	echo "Required environment variables:"
	missing_vars=0
	if [ -z "${GEO_DB_DIAL_ADDR+x}" ]; then
		echo "  GEO_DB_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  GEO_DB_DIAL_ADDR=$GEO_DB_DIAL_ADDR"
	fi
	
	if [ -z "${GEO_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "  GEO_SERVICE_GRPC_BIND_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  GEO_SERVICE_GRPC_BIND_ADDR=$GEO_SERVICE_GRPC_BIND_ADDR"
	fi
	
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "  JAEGER_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
		

	if [ "$missing_vars" -gt 0 ]; then
		echo "Aborting due to missing environment variables"
		return 1
	fi

	geo_service_process
	
	wait
}

run_all
