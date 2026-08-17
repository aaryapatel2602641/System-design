'''
Automated CRUD checker for rest_api.py

HOW TO USE:
    1. In one terminal, start the server:   python rest_api.py
    2. In a second terminal, run this:       python test_api.py

It exercises every CRUD operation on consumer, product, and order,
and prints PASS / FAIL for each check.

Requires the 'requests' library:  pip install requests
'''

import requests

BASE = "http://localhost:5001"

passed = 0
failed = 0


def check(label, condition):
    """Print PASS/FAIL for a single assertion and keep a running tally."""
    global passed, failed
    if condition:
        passed += 1
        print("  PASS  - {}".format(label))
    else:
        failed += 1
        print("  FAIL  - {}".format(label))


def section(title):
    print("\n=== {} ===".format(title))


# ==================================================================
#  CONSUMER
# ==================================================================
section("CONSUMER")

# CREATE
r = requests.post(BASE + "/consumer", json={"name": "TestUser", "email": "t@mail.com"})
check("POST /consumer returns 201", r.status_code == 201)
new_consumer_id = r.json().get("id")
check("created consumer has an id", new_consumer_id is not None)

# READ (all)
r = requests.get(BASE + "/consumer")
check("GET /consumer returns 200", r.status_code == 200)
check("GET /consumer returns a list", isinstance(r.json(), list))

# READ (one)
r = requests.get(BASE + "/consumer/{}".format(new_consumer_id))
check("GET /consumer/<id> returns 200", r.status_code == 200)
check("fetched consumer name is correct", r.json().get("name") == "TestUser")

# UPDATE
r = requests.put(BASE + "/consumer/{}".format(new_consumer_id), json={"email": "new@mail.com"})
check("PUT /consumer/<id> returns 200", r.status_code == 200)
check("consumer email was updated", r.json().get("email") == "new@mail.com")

# DELETE
r = requests.delete(BASE + "/consumer/{}".format(new_consumer_id))
check("DELETE /consumer/<id> returns 200", r.status_code == 200)
r = requests.get(BASE + "/consumer/{}".format(new_consumer_id))
check("consumer is gone after delete (404)", r.status_code == 404)


# ==================================================================
#  PRODUCT
# ==================================================================
section("PRODUCT")

# CREATE
r = requests.post(BASE + "/product", json={"name": "TestItem", "price": 99})
check("POST /product returns 201", r.status_code == 201)
new_product_id = r.json().get("id")
check("created product has an id", new_product_id is not None)

# READ (all)
r = requests.get(BASE + "/product")
check("GET /product returns 200", r.status_code == 200)
check("GET /product returns a list", isinstance(r.json(), list))

# READ (one)
r = requests.get(BASE + "/product/{}".format(new_product_id))
check("GET /product/<id> returns 200", r.status_code == 200)
check("fetched product price is correct", r.json().get("price") == 99)

# UPDATE
r = requests.put(BASE + "/product/{}".format(new_product_id), json={"price": 150})
check("PUT /product/<id> returns 200", r.status_code == 200)
check("product price was updated", r.json().get("price") == 150)

# DELETE
r = requests.delete(BASE + "/product/{}".format(new_product_id))
check("DELETE /product/<id> returns 200", r.status_code == 200)
r = requests.get(BASE + "/product/{}".format(new_product_id))
check("product is gone after delete (404)", r.status_code == 404)


# ==================================================================
#  ORDER  (needs a real consumer + product to reference)
# ==================================================================
section("ORDER")

# set up a consumer and a product for the order to point at
cid = requests.post(BASE + "/consumer", json={"name": "Buyer", "email": "b@mail.com"}).json()["id"]
pid = requests.post(BASE + "/product", json={"name": "Widget", "price": 20}).json()["id"]

# CREATE
r = requests.post(BASE + "/order", json={"consumer_id": cid, "product_id": pid, "quantity": 4})
check("POST /order returns 201", r.status_code == 201)
new_order_id = r.json().get("id")
check("created order has an id", new_order_id is not None)

# CREATE with a bad reference should be rejected
r = requests.post(BASE + "/order", json={"consumer_id": 99999, "product_id": pid, "quantity": 1})
check("POST /order with bad consumer_id returns 400", r.status_code == 400)

# READ (all)
r = requests.get(BASE + "/order")
check("GET /order returns 200", r.status_code == 200)
check("GET /order returns a list", isinstance(r.json(), list))

# READ (one)
r = requests.get(BASE + "/order/{}".format(new_order_id))
check("GET /order/<id> returns 200", r.status_code == 200)
check("fetched order quantity is correct", r.json().get("quantity") == 4)

# UPDATE
r = requests.put(BASE + "/order/{}".format(new_order_id), json={"quantity": 10})
check("PUT /order/<id> returns 200", r.status_code == 200)
check("order quantity was updated", r.json().get("quantity") == 10)

# DELETE
r = requests.delete(BASE + "/order/{}".format(new_order_id))
check("DELETE /order/<id> returns 200", r.status_code == 200)
r = requests.get(BASE + "/order/{}".format(new_order_id))
check("order is gone after delete (404)", r.status_code == 404)

# clean up the helper records
requests.delete(BASE + "/consumer/{}".format(cid))
requests.delete(BASE + "/product/{}".format(pid))


# ==================================================================
#  SUMMARY
# ==================================================================
print("\n" + "=" * 40)
print("RESULT: {} passed, {} failed".format(passed, failed))
print("=" * 40)