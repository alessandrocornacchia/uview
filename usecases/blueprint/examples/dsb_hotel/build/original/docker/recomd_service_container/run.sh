#!/bin/bash

WORKSPACE_NAME="recomd_service_container"
WORKSPACE_DIR=$(pwd)

usage() { 
	echo "Usage: $0 [-h]" 1>&2
	echo "  Required environment variables:"
	
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "    JAEGER_DIAL_ADDR (missing)"
	else
		echo "    JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	if [ -z "${RECOMD_DB_DIAL_ADDR+x}" ]; then
		echo "    RECOMD_DB_DIAL_ADDR (missing)"
	else
		echo "    RECOMD_DB_DIAL_ADDR=$RECOMD_DB_DIAL_ADDR"
	fi
	if [ -z "${RECOMD_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "    RECOMD_SERVICE_GRPC_BIND_ADDR (missing)"
	else
		echo "    RECOMD_SERVICE_GRPC_BIND_ADDR=$RECOMD_SERVICE_GRPC_BIND_ADDR"
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


recomd_service_process() {
	cd $WORKSPACE_DIR
	
	if [ -z "${RECOMD_DB_DIAL_ADDR+x}" ]; then
		if ! recomd_db_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		if ! jaeger_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${RECOMD_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		if ! recomd_service_grpc_bind_addr; then
			return $?
		fi
	fi

	run_recomd_service_process() {
		
        cd recomd_service_process
        ./recomd_service_process --recomd_db.dial_addr=$RECOMD_DB_DIAL_ADDR --jaeger.dial_addr=$JAEGER_DIAL_ADDR --recomd_service.grpc.bind_addr=$RECOMD_SERVICE_GRPC_BIND_ADDR &
        RECOMD_SERVICE_PROCESS=$!
        return $?

	}

	if run_recomd_service_process; then
		if [ -z "${RECOMD_SERVICE_PROCESS+x}" ]; then
			echo "${WORKSPACE_NAME} error starting recomd_service_process: function recomd_service_process did not set RECOMD_SERVICE_PROCESS"
			return 1
		else
			echo "${WORKSPACE_NAME} started recomd_service_process"
			return 0
		fi
	else
		exitcode=$?
		echo "${WORKSPACE_NAME} aborting recomd_service_process due to exitcode ${exitcode} from recomd_service_process"
		return $exitcode
	fi
}


run_all() {
	echo "Running recomd_service_container"

	# Check that all necessary environment variables are set
	echo "Required environment variables:"
	missing_vars=0
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "  JAEGER_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	
	if [ -z "${RECOMD_DB_DIAL_ADDR+x}" ]; then
		echo "  RECOMD_DB_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RECOMD_DB_DIAL_ADDR=$RECOMD_DB_DIAL_ADDR"
	fi
	
	if [ -z "${RECOMD_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "  RECOMD_SERVICE_GRPC_BIND_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RECOMD_SERVICE_GRPC_BIND_ADDR=$RECOMD_SERVICE_GRPC_BIND_ADDR"
	fi
		

	if [ "$missing_vars" -gt 0 ]; then
		echo "Aborting due to missing environment variables"
		return 1
	fi

	recomd_service_process
	
	wait
}

run_all
