#!/bin/bash

WORKSPACE_NAME="frontend_service_container"
WORKSPACE_DIR=$(pwd)

usage() { 
	echo "Usage: $0 [-h]" 1>&2
	echo "  Required environment variables:"
	
	if [ -z "${FRONTEND_SERVICE_HTTP_BIND_ADDR+x}" ]; then
		echo "    FRONTEND_SERVICE_HTTP_BIND_ADDR (missing)"
	else
		echo "    FRONTEND_SERVICE_HTTP_BIND_ADDR=$FRONTEND_SERVICE_HTTP_BIND_ADDR"
	fi
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "    JAEGER_DIAL_ADDR (missing)"
	else
		echo "    JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	if [ -z "${PROFILE_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "    PROFILE_SERVICE_GRPC_DIAL_ADDR (missing)"
	else
		echo "    PROFILE_SERVICE_GRPC_DIAL_ADDR=$PROFILE_SERVICE_GRPC_DIAL_ADDR"
	fi
	if [ -z "${RECOMD_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "    RECOMD_SERVICE_GRPC_DIAL_ADDR (missing)"
	else
		echo "    RECOMD_SERVICE_GRPC_DIAL_ADDR=$RECOMD_SERVICE_GRPC_DIAL_ADDR"
	fi
	if [ -z "${RESERV_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "    RESERV_SERVICE_GRPC_DIAL_ADDR (missing)"
	else
		echo "    RESERV_SERVICE_GRPC_DIAL_ADDR=$RESERV_SERVICE_GRPC_DIAL_ADDR"
	fi
	if [ -z "${SEARCH_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "    SEARCH_SERVICE_GRPC_DIAL_ADDR (missing)"
	else
		echo "    SEARCH_SERVICE_GRPC_DIAL_ADDR=$SEARCH_SERVICE_GRPC_DIAL_ADDR"
	fi
	if [ -z "${USER_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "    USER_SERVICE_GRPC_DIAL_ADDR (missing)"
	else
		echo "    USER_SERVICE_GRPC_DIAL_ADDR=$USER_SERVICE_GRPC_DIAL_ADDR"
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


frontend_service_process() {
	cd $WORKSPACE_DIR
	
	if [ -z "${SEARCH_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		if ! search_service_grpc_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		if ! jaeger_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${PROFILE_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		if ! profile_service_grpc_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${RECOMD_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		if ! recomd_service_grpc_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${USER_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		if ! user_service_grpc_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${RESERV_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		if ! reserv_service_grpc_dial_addr; then
			return $?
		fi
	fi

	if [ -z "${FRONTEND_SERVICE_HTTP_BIND_ADDR+x}" ]; then
		if ! frontend_service_http_bind_addr; then
			return $?
		fi
	fi

	run_frontend_service_process() {
		
        cd frontend_service_process
        ./frontend_service_process --search_service.grpc.dial_addr=$SEARCH_SERVICE_GRPC_DIAL_ADDR --jaeger.dial_addr=$JAEGER_DIAL_ADDR --profile_service.grpc.dial_addr=$PROFILE_SERVICE_GRPC_DIAL_ADDR --recomd_service.grpc.dial_addr=$RECOMD_SERVICE_GRPC_DIAL_ADDR --user_service.grpc.dial_addr=$USER_SERVICE_GRPC_DIAL_ADDR --reserv_service.grpc.dial_addr=$RESERV_SERVICE_GRPC_DIAL_ADDR --frontend_service.http.bind_addr=$FRONTEND_SERVICE_HTTP_BIND_ADDR &
        FRONTEND_SERVICE_PROCESS=$!
        return $?

	}

	if run_frontend_service_process; then
		if [ -z "${FRONTEND_SERVICE_PROCESS+x}" ]; then
			echo "${WORKSPACE_NAME} error starting frontend_service_process: function frontend_service_process did not set FRONTEND_SERVICE_PROCESS"
			return 1
		else
			echo "${WORKSPACE_NAME} started frontend_service_process"
			return 0
		fi
	else
		exitcode=$?
		echo "${WORKSPACE_NAME} aborting frontend_service_process due to exitcode ${exitcode} from frontend_service_process"
		return $exitcode
	fi
}


run_all() {
	echo "Running frontend_service_container"

	# Check that all necessary environment variables are set
	echo "Required environment variables:"
	missing_vars=0
	if [ -z "${FRONTEND_SERVICE_HTTP_BIND_ADDR+x}" ]; then
		echo "  FRONTEND_SERVICE_HTTP_BIND_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  FRONTEND_SERVICE_HTTP_BIND_ADDR=$FRONTEND_SERVICE_HTTP_BIND_ADDR"
	fi
	
	if [ -z "${JAEGER_DIAL_ADDR+x}" ]; then
		echo "  JAEGER_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  JAEGER_DIAL_ADDR=$JAEGER_DIAL_ADDR"
	fi
	
	if [ -z "${PROFILE_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "  PROFILE_SERVICE_GRPC_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  PROFILE_SERVICE_GRPC_DIAL_ADDR=$PROFILE_SERVICE_GRPC_DIAL_ADDR"
	fi
	
	if [ -z "${RECOMD_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "  RECOMD_SERVICE_GRPC_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RECOMD_SERVICE_GRPC_DIAL_ADDR=$RECOMD_SERVICE_GRPC_DIAL_ADDR"
	fi
	
	if [ -z "${RESERV_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "  RESERV_SERVICE_GRPC_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  RESERV_SERVICE_GRPC_DIAL_ADDR=$RESERV_SERVICE_GRPC_DIAL_ADDR"
	fi
	
	if [ -z "${SEARCH_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "  SEARCH_SERVICE_GRPC_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  SEARCH_SERVICE_GRPC_DIAL_ADDR=$SEARCH_SERVICE_GRPC_DIAL_ADDR"
	fi
	
	if [ -z "${USER_SERVICE_GRPC_DIAL_ADDR+x}" ]; then
		echo "  USER_SERVICE_GRPC_DIAL_ADDR (missing)"
		missing_vars=$((missing_vars+1))
	else
		echo "  USER_SERVICE_GRPC_DIAL_ADDR=$USER_SERVICE_GRPC_DIAL_ADDR"
	fi
		

	if [ "$missing_vars" -gt 0 ]; then
		echo "Aborting due to missing environment variables"
		return 1
	fi

	frontend_service_process
	
	wait
}

run_all
