#!/bin/bash

WORKSPACE_NAME="user_service_container"
WORKSPACE_DIR=$(pwd)

usage() { 
	echo "Usage: $0 [-h]" 1>&2
	echo "  Required environment variables:"
	
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "    JAEGER_DIAL_ADDR (missing)"
	else
		echo "    JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	if [ -z "${USER_DB_DIAL_ADDR+x}" ]; then
		echo "    USER_DB_DIAL_ADDR (missing)"
	else
		echo "    USER_DB_DIAL_ADDR=$USER_DB_DIAL_ADDR"
	fi
	if [ -z "${USER_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "    USER_SERVICE_GRPC_BIND_ADDR (missing)"
	else
		echo "    USER_SERVICE_GRPC_BIND_ADDR=$USER_SERVICE_GRPC_BIND_ADDR"
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


user_service_process() {
	cd $WORKSPACE_DIR
	
	if [ -z "${USER_DB_DIAL_ADDR+x}" ]; then
		if ! user_db_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		if ! jaeger_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${USER_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		if ! user_service_grpc_bind_addr; then
			return $?
		fi
	fi

	run_user_service_process() {
		
        cd user_service_process
        ./user_service_process --user_db.dial_addr=$USER_DB_DIAL_ADDR --jaeger.dial_addr=$JAEGER_DIAL_ADDR --user_service.grpc.bind_addr=$USER_SERVICE_GRPC_BIND_ADDR &
        USER_SERVICE_PROCESS=$!
        return $?

	}

	if run_user_service_process; then
		if [ -z "${USER_SERVICE_PROCESS+x}" ]; then
			echo "${WORKSPACE_NAME} error starting user_service_process: function user_service_process did not set USER_SERVICE_PROCESS"
			return 1
		else
			echo "${WORKSPACE_NAME} started user_service_process"
			return 0
		fi
	else
		exitcode=$?
		echo "${WORKSPACE_NAME} aborting user_service_process due to exitcode ${exitcode} from user_service_process"
		return $exitcode
	fi
}


run_all() {
	echo "Running user_service_container"

	# Check that all necessary environment variables are set
	echo "Required environment variables:"
	missing_vars=0
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "  JAEGER_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	
	if [ -z "${USER_DB_DIAL_ADDR+x}" ]; then
		echo "  USER_DB_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  USER_DB_DIAL_ADDR=$USER_DB_DIAL_ADDR"
	fi
	
	if [ -z "${USER_SERVICE_GRPC_BIND_ADDR+x}" ]; then
		echo "  USER_SERVICE_GRPC_BIND_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  USER_SERVICE_GRPC_BIND_ADDR=$USER_SERVICE_GRPC_BIND_ADDR"
	fi
		

	if [ "$missing_vars" -gt 0 ]; then
		echo "Aborting due to missing environment variables"
		return 1
	fi

	user_service_process
	
	wait
}

run_all
