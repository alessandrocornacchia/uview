package workload

import (
	"fmt"
	"math/rand"
	"net/url"
	"strconv"
)

var letters = []rune("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
var decimals = []rune("0123456789")

// From: https://stackoverflow.com/questions/22892120/how-to-generate-a-random-string-of-a-fixed-length-in-go
func randStringRunes(n int) string {
	b := make([]rune, n)
	for i := range b {
		b[i] = letters[rand.Intn(len(letters))]
	}
	return string(b)
}

func randStringDecRunes(n int) int64 {
	b := make([]rune, n)
	for i := range b {
		b[i] = decimals[rand.Intn(len(decimals))]
	}
	str := string(b)
	i, _ := strconv.ParseInt(str, 10, 64)
	return i
}

func sn_ReadUserTimeline(is_original bool) url.Values {
	user_id := rand.Intn(962)
	start := rand.Intn(100)
	stop := start + 10
	data := url.Values{}
	data.Add("user_id", prepareArg(user_id, is_original))
	data.Add("start", prepareArg(start, is_original))
	data.Add("stop", prepareArg(stop, is_original))
	return data
}

func sn_ReadHomeTimeline(is_original bool) url.Values {
	user_id := rand.Intn(962)
	start := rand.Intn(100)
	stop := start + 10
	data := url.Values{}
	data.Add("user_id", prepareArg(user_id, is_original))
	data.Add("start", prepareArg(start, is_original))
	data.Add("stop", prepareArg(stop, is_original))
	return data
}

func sn_ComposePost(is_original bool) url.Values {
	user_id := rand.Intn(962)
	username := "username_" + fmt.Sprintf("%d", user_id)
	num_urls := rand.Intn(5)
	num_media := rand.Intn(4)
	num_user_mentions := rand.Intn(5)
	text := randStringRunes(256)
	var media_types []string
	var media_ids []int64

	seen_user_ids := make(map[int]bool)
	seen_user_ids[user_id] = true
	for i := 0; i < num_user_mentions; i++ {
		var mention_id int
		for {
			mention_id = rand.Intn(962)
			if _, ok := seen_user_ids[mention_id]; !ok {
				break
			}
		}
		seen_user_ids[mention_id] = true
		text += " @username_" + fmt.Sprintf("%d", mention_id)
	}

	for i := 0; i < num_urls; i++ {
		text += " http://" + randStringRunes(64)
	}

	for i := 0; i < num_media; i++ {
		media_id := randStringDecRunes(18)
		media_ids = append(media_ids, media_id)
		media_types = append(media_types, "png")
	}

	data := url.Values{}
	data.Add("user_id", prepareArg(user_id, is_original))
	data.Add("username", prepareArg(username, is_original))
	data.Add("text", prepareArg(text, is_original))
	data.Add("post_type", prepareArg("0", is_original))
	if num_media > 0 {
		data.Add("media_ids", prepareArg(media_ids, is_original))
		data.Add("media_types", prepareArg(media_types, is_original))
	}
	return data
}
