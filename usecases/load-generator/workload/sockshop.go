package workload

import (
	"math/rand"
	"net/url"
	"strconv"
)

// generateObjectID generates a valid MongoDB ObjectID-like string (24 hex characters)
func generateObjectID() string {
	chars := "abcdef0123456789"
	result := ""
	for i := 0; i < 24; i++ {
		result += string(chars[rand.Intn(len(chars))])
	}
	return result
}

// GetCart - List items in cart for current logged in user, or for the current session if not logged in
func sockshop_GetCart(is_original bool) url.Values {
	// Generate a random sessionID (could be empty for new sessions)
	sessionID := ""
	if rand.Intn(100) > 20 { // 80% chance of having a sessionID
		sessionID = generateObjectID()
	}
	
	data := url.Values{}
	data.Add("sessionID", prepareArg(sessionID, is_original))
	return data
}

// DeleteCart - Deletes the entire cart for a user/session
func sockshop_DeleteCart(is_original bool) url.Values {
	sessionID := generateObjectID()
	
	data := url.Values{}
	data.Add("sessionID", prepareArg(sessionID, is_original))
	return data
}

// RemoveItem - Removes an item from the user/session's cart
func sockshop_RemoveItem(is_original bool) url.Values {
	sessionID := generateObjectID()
	// Generate sock item ID using actual sock names
	sockItems := []string{
		"Weave special", "Nerd leg", "Crossed", "SuperSport XL", "Holy",
		"YouTube.sock", "Figueroa", "Classic", "Colourful", "Cat socks",
	}
	itemID := sockItems[rand.Intn(len(sockItems))]
	
	data := url.Values{}
	data.Add("sessionID", prepareArg(sessionID, is_original))
	data.Add("itemID", prepareArg(itemID, is_original))
	return data
}

// AddItem - Adds an item to the user/session's cart
func sockshop_AddItem(is_original bool) url.Values {
	sessionID := ""
	if rand.Intn(100) > 30 { // 70% chance of having existing session
		sessionID = generateObjectID()
	}
	
	sockItems := []string{
		"Weave special", "Nerd leg", "Crossed", "SuperSport XL", "Holy",
		"YouTube.sock", "Figueroa", "Classic", "Colourful", "Cat socks",
	}
	itemID := sockItems[rand.Intn(len(sockItems))]
	
	data := url.Values{}
	data.Add("sessionID", prepareArg(sessionID, is_original))
	data.Add("itemID", prepareArg(itemID, is_original))
	return data
}

// UpdateItem - Update item quantity in the user/session's cart
func sockshop_UpdateItem(is_original bool) url.Values {
	sessionID := ""
	if rand.Intn(100) > 30 {
		sessionID = generateObjectID()
	}
	
	sockItems := []string{
		"Weave special", "Nerd leg", "Crossed", "SuperSport XL", "Holy",
		"YouTube.sock", "Figueroa", "Classic", "Colourful", "Cat socks",
	}
	itemID := sockItems[rand.Intn(len(sockItems))]
	quantity := rand.Intn(5) + 1 // 1-5 items
	
	data := url.Values{}
	data.Add("sessionID", prepareArg(sessionID, is_original))
	data.Add("itemID", prepareArg(itemID, is_original))
	data.Add("quantity", prepareArg(quantity, is_original))
	return data
}

// ListItems - List socks that match any of the tags specified
func sockshop_ListItems(is_original bool) url.Values {
	allTags := []string{"brown", "geek", "formal", "blue", "skin", "red", "action", "sport", "black", "magic", "green"}
	
	// Select 1-3 random tags
	numTags := rand.Intn(3) + 1
	tags := make([]string, numTags)
	for i := 0; i < numTags; i++ {
		tags[i] = allTags[rand.Intn(len(allTags))]
	}
	
	// Random order (can be empty)
	orders := []string{"", "name", "price", "quantity"}
	order := orders[rand.Intn(len(orders))]
	
	pageNum := 1 //rand.Intn(5) + 1  // 1-5
	pageSize := 20 //rand.Intn(20) + 5 // 5-24
	
	data := url.Values{}
	
	// Add tags as a single JSON array parameter
	data.Add("tags", prepareArg(tags, is_original))
	data.Add("order", prepareArg(order, is_original))
	data.Add("pageNum", prepareArg(pageNum, is_original))
	data.Add("pageSize", prepareArg(pageSize, is_original))
	return data
}

// GetSock - Gets details about a Sock
func sockshop_GetSock(is_original bool) url.Values {
	// Use actual sock names from LoadCatalogue function, converted to IDs
	sockItems := []string{
		"Weave special", "Nerd leg", "Crossed", "SuperSport XL", "Holy",
		"YouTube.sock", "Figueroa", "Classic", "Colourful", "Cat socks",
	}
	itemID := sockItems[rand.Intn(len(sockItems))]
	
	data := url.Values{}
	data.Add("itemID", prepareArg(itemID, is_original))
	return data
}

// ListTags - Lists all tags
func sockshop_ListTags(is_original bool) url.Values {
	data := url.Values{}
	// No parameters needed for listing tags
	return data
}

// NewOrder - Place an order for the specified items
func sockshop_NewOrder(is_original bool) url.Values {
	customerID := generateObjectID()  // Use proper ObjectID format
	addressID := generateObjectID()
	cardID := generateObjectID()
	cartID := generateObjectID()
	
	data := url.Values{}
	data.Add("customerID", prepareArg(customerID, is_original))
	data.Add("addressID", prepareArg(addressID, is_original))
	data.Add("cardID", prepareArg(cardID, is_original))
	data.Add("cartID", prepareArg(cartID, is_original))
	return data
}

// GetOrders - Get all orders for a customer, sorted by date
func sockshop_GetOrders(is_original bool) url.Values {
	userID := generateObjectID()  // Use proper ObjectID format
	
	data := url.Values{}
	data.Add("userID", prepareArg(userID, is_original))
	return data
}

// GetOrder - Get an order by ID
func sockshop_GetOrder(is_original bool) url.Values {
	orderID := generateObjectID()  // Use proper ObjectID format
	
	data := url.Values{}
	data.Add("orderID", prepareArg(orderID, is_original))
	return data
}

// Login - Log in to an existing user account
func sockshop_Login(is_original bool) url.Values {
	sessionID := ""
	if rand.Intn(100) > 50 {
		sessionID = generateObjectID()
	}
	
	userID := rand.Intn(500)
	username := "sockshop_user_" + strconv.Itoa(userID)
	password := "password" + strconv.Itoa(userID)
	
	data := url.Values{}
	data.Add("sessionID", prepareArg(sessionID, is_original))
	data.Add("username", prepareArg(username, is_original))
	data.Add("password", prepareArg(password, is_original))
	return data
}

// Register - Register a new user account
func sockshop_Register(is_original bool) url.Values {
	sessionID := ""
	if rand.Intn(100) > 50 {
		sessionID = generateObjectID()
	}
	
	userID := rand.Intn(10000)
	username := "new_user_" + strconv.Itoa(userID)
	password := "newpass" + strconv.Itoa(userID)
	email := username + "@sockshop.com"
	first := "First" + strconv.Itoa(userID)
	last := "Last" + strconv.Itoa(userID)
	
	data := url.Values{}
	data.Add("sessionID", prepareArg(sessionID, is_original))
	data.Add("username", prepareArg(username, is_original))
	data.Add("password", prepareArg(password, is_original))
	data.Add("email", prepareArg(email, is_original))
	data.Add("first", prepareArg(first, is_original))
	data.Add("last", prepareArg(last, is_original))
	return data
}

// GetUser - Look up a user by customer ID
func sockshop_GetUser(is_original bool) url.Values {
	userID := generateObjectID()  // Use proper ObjectID format
	
	data := url.Values{}
	data.Add("userID", prepareArg(userID, is_original))
	return data
}

// GetAddress - Look up an address by address ID
func sockshop_GetAddress(is_original bool) url.Values {
	addressID := generateObjectID()  // Use proper ObjectID format
	
	data := url.Values{}
	data.Add("addressID", prepareArg(addressID, is_original))
	return data
}

// PostAddress - Adds a new address for a customer
func sockshop_PostAddress(is_original bool) url.Values {
	// userID := generateObjectID()  // Use proper ObjectID format
	
	streets := []string{"Main St", "Oak Ave", "Pine Rd", "Elm St", "Cedar Ln"}
	countries := []string{"USA", "UK", "Germany", "France", "Canada"}
	cities := []string{"New York", "London", "Berlin", "Paris", "Toronto"}
	
	street := streets[rand.Intn(len(streets))]
	number := strconv.Itoa(rand.Intn(9999) + 1)
	country := countries[rand.Intn(len(countries))]
	city := cities[rand.Intn(len(cities))]
	postCode := strconv.Itoa(rand.Intn(99999) + 10000)
	
	data := url.Values{}
	data.Add("userID", prepareArg("b58a67ef-dc90-4be3-97c9-ec6e2f243705", is_original))
	data.Add("street", prepareArg(street, is_original))
	data.Add("number", prepareArg(number, is_original))
	data.Add("country", prepareArg(country, is_original))
	data.Add("city", prepareArg(city, is_original))
	data.Add("postCode", prepareArg(postCode, is_original))
	return data
}

// GetCard - Look up a card by card id
func sockshop_GetCard(is_original bool) url.Values {
	cardID := generateObjectID()  // Use proper ObjectID format
	
	data := url.Values{}
	data.Add("cardID", prepareArg(cardID, is_original))
	return data
}

// PostCard - Adds a new card for a customer
func sockshop_PostCard(is_original bool) url.Values {
	userID := generateObjectID()  // Use proper ObjectID format
	
	// Generate fake credit card number
	longNum := "4"
	for i := 0; i < 15; i++ {
		longNum += strconv.Itoa(rand.Intn(10))
	}
	
	// Generate expiry date (MM/YY format)
	month := rand.Intn(12) + 1
	year := rand.Intn(10) + 24 // 2024-2033
	expires := ""
	if month < 10 {
		expires = "0" + strconv.Itoa(month)
	} else {
		expires = strconv.Itoa(month)
	}
	expires += "/" + strconv.Itoa(year)
	
	// Generate CCV
	ccv := ""
	for i := 0; i < 3; i++ {
		ccv += strconv.Itoa(rand.Intn(10))
	}
	
	data := url.Values{}
	data.Add("userID", prepareArg(userID, is_original))
	data.Add("longNum", prepareArg(longNum, is_original))
	data.Add("expires", prepareArg(expires, is_original))
	data.Add("ccv", prepareArg(ccv, is_original))
	return data
}

// LoadCatalogue - Loads the catalogue in the catalogue service
func sockshop_LoadCatalogue(is_original bool) url.Values {
	data := url.Values{}
	// No parameters needed for loading catalogue
	return data
}
