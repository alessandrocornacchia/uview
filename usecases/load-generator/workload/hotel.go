package workload

import (
	"math/rand"
	"net/url"
	"strconv"
)

func UserHandler(is_original bool) url.Values {
	id := rand.Intn(500)
	username := "Cornell_" + strconv.Itoa(id)
	password := ""
	for i := 0; i < 10; i += 1 {
		password += strconv.Itoa(id)
	}
	data := url.Values{}
	data.Add("username", prepareArg(username, is_original))
	data.Add("password", prepareArg(password, is_original))
	return data
}

func SearchHandler(is_original bool) url.Values {
	lat := 38.0235
	lon := -122.095
	lat = lat + (float64(rand.Intn(481))-240.5)/1000.0
	lon = lon + (float64(rand.Intn(325))-157.0)/1000.0
	inDay := rand.Intn(14) + 9
	outDay := rand.Intn(24-1-inDay) + inDay + 1
	var inDate, outDate string
	if inDay > 9 {
		inDate = "2015-04-" + strconv.Itoa(inDay)
	} else {
		inDate = "2015-04-0" + strconv.Itoa(inDay)
	}
	if outDay > 9 {
		outDate = "2015-04-" + strconv.Itoa(outDay)
	} else {
		outDate = "2015-04-0" + strconv.Itoa(outDay)
	}
	data := url.Values{}
	data.Add("lat", prepareArg(lat, is_original))
	data.Add("lon", prepareArg(lon, is_original))
	data.Add("inDate", prepareArg(inDate, is_original))
	data.Add("outDate", prepareArg(outDate, is_original))
	return data
}

func RecommendHandler(is_original bool) url.Values {
	lat := 38.0235
	lon := -122.095
	lat = lat + (float64(rand.Intn(481))-240.5)/1000.0
	lon = lon + (float64(rand.Intn(325))-157.0)/1000.0
	req := ""
	rnum := rand.Intn(100)
	if rnum < 33 {
		req = "dis"
	} else if rnum < 66 {
		req = "rate"
	} else {
		req = "price"
	}
	data := url.Values{}
	data.Add("lat", prepareArg(lat, is_original))
	data.Add("lon", prepareArg(lon, is_original))
	data.Add("require", req)
	return data
}

func ReservationHandler(is_original bool) url.Values {
	inDay := rand.Intn(14) + 9
	outDay := rand.Intn(24-1-inDay) + inDay + 1
	var inDate, outDate string
	if inDay > 9 {
		inDate = "2015-04-" + strconv.Itoa(inDay)
	} else {
		inDate = "2015-04-0" + strconv.Itoa(inDay)
	}
	if outDay > 9 {
		outDate = "2015-04-" + strconv.Itoa(outDay)
	} else {
		outDate = "2015-04-0" + strconv.Itoa(outDay)
	}
	hotelid := rand.Intn(80) + 1
	hotelId := strconv.Itoa(hotelid)
	id := rand.Intn(500)
	username := "Cornell_" + strconv.Itoa(id)
	password := ""
	for i := 0; i < 10; i += 1 {
		password += strconv.Itoa(id)
	}
	customerName := username
	roomNUmber := 1
	data := url.Values{}
	data.Add("inDate", prepareArg(inDate, is_original))
	data.Add("outDate", prepareArg(outDate, is_original))
	data.Add("hotelId", prepareArg(hotelId, is_original))
	data.Add("username", prepareArg(username, is_original))
	data.Add("password", prepareArg(password, is_original))
	data.Add("customerName", prepareArg(customerName, is_original))
	data.Add("roomNumber", prepareArg(roomNUmber, is_original))
	return data
}
