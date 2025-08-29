package workload

import (
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"reflect"
)

type WorkloadRegistry struct {
	argGenFuncMap map[string]func(bool) url.Values
}

func NewWorkloadRegistry() *WorkloadRegistry {
	m := make(map[string]func(bool) url.Values)
	// Hotel Reservation API
	m["hotel_UserHandler"] = UserHandler
	m["hotel_SearchHandler"] = SearchHandler
	m["hotel_RecommendHandler"] = RecommendHandler
	m["hotel_ReservationHandler"] = ReservationHandler

	// Social Network API
	m["sn_ReadHomeTimeline"] = sn_ReadHomeTimeline
	m["sn_ReadUserTimeline"] = sn_ReadUserTimeline
	m["sn_ComposePost"] = sn_ComposePost

	// SockShop API
	m["sockshop_GetCart"] = sockshop_GetCart
	m["sockshop_DeleteCart"] = sockshop_DeleteCart
	m["sockshop_RemoveItem"] = sockshop_RemoveItem
	m["sockshop_AddItem"] = sockshop_AddItem
	m["sockshop_UpdateItem"] = sockshop_UpdateItem
	m["sockshop_ListItems"] = sockshop_ListItems
	m["sockshop_GetSock"] = sockshop_GetSock
	m["sockshop_ListTags"] = sockshop_ListTags
	m["sockshop_NewOrder"] = sockshop_NewOrder
	m["sockshop_GetOrders"] = sockshop_GetOrders
	m["sockshop_GetOrder"] = sockshop_GetOrder
	m["sockshop_Login"] = sockshop_Login
	m["sockshop_Register"] = sockshop_Register
	m["sockshop_GetUser"] = sockshop_GetUser
	m["sockshop_GetAddress"] = sockshop_GetAddress
	m["sockshop_PostAddress"] = sockshop_PostAddress
	m["sockshop_GetCard"] = sockshop_GetCard
	m["sockshop_PostCard"] = sockshop_PostCard
	m["sockshop_LoadCatalogue"] = sockshop_LoadCatalogue

	// Leaf API
	// m["leaf_Leaf"] = leaf_Leaf
	return &WorkloadRegistry{argGenFuncMap: m}
}

func (r *WorkloadRegistry) GetGeneratorFunction(name string) func(bool) url.Values {
	if v, ok := r.argGenFuncMap[name]; ok {
		return v
	}
	log.Println("Returning nil for", name)
	return nil
}

func prepareArg(arg interface{}, is_original bool) string {
	if is_original && reflect.TypeOf(arg).Kind() == reflect.String {
		return fmt.Sprintf("%s", arg)
	}
	bytes, _ := json.Marshal(arg)
	return string(bytes)
}
