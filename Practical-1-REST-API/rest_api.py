'''
Resource-based REST API demonstrating full CRUD for three resources:
    - consumer   (id, name, email)
    - product    (id, name, price)
    - order      (id, consumer_id, product_id, quantity)

Pattern (same style as the flask_restful example):
    /<resource>          -> GET all,  POST create
    /<resource>/<id>     -> GET one,  PUT update,  DELETE remove

Run:  python rest_api.py     (serves on http://localhost:5001)
'''

from flask import Flask
from flask_restful import Api, Resource, reqparse

app = Flask(__name__)
api = Api(app)

# ---------------- In-memory data stores ----------------
# Each is a dict keyed by integer id, with a separate counter for new ids.
consumers = {
    1: {"id": 1, "name": "Nicholas", "email": "nick@mail.com"},
    2: {"id": 2, "name": "Elvin",    "email": "elvin@mail.com"},
}
products = {
    1: {"id": 1, "name": "Laptop", "price": 1000},
    2: {"id": 2, "name": "Phone",  "price": 500},
}
orders = {
    1: {"id": 1, "consumer_id": 1, "product_id": 2, "quantity": 3},
}

# id counters (next id to assign)
counters = {"consumer": 3, "product": 3, "order": 2}


def next_id(kind):
    nid = counters[kind]
    counters[kind] += 1
    return nid


# ==================================================================
#  CONSUMER
# ==================================================================
class ConsumerList(Resource):
    def get(self):                                   # GET /consumer  -> all
        return list(consumers.values()), 200

    def post(self):                                  # POST /consumer -> create
        parser = reqparse.RequestParser()
        parser.add_argument("name", required=True)
        parser.add_argument("email", required=True)
        args = parser.parse_args()

        nid = next_id("consumer")
        consumers[nid] = {"id": nid, "name": args["name"], "email": args["email"]}
        return consumers[nid], 201


class Consumer(Resource):
    def get(self, cid):                              # GET /consumer/<id>
        if cid in consumers:
            return consumers[cid], 200
        return {"error": "Consumer not found"}, 404

    def put(self, cid):                              # PUT /consumer/<id> -> update
        parser = reqparse.RequestParser()
        parser.add_argument("name")
        parser.add_argument("email")
        args = parser.parse_args()

        if cid not in consumers:
            return {"error": "Consumer not found"}, 404

        if args["name"] is not None:
            consumers[cid]["name"] = args["name"]
        if args["email"] is not None:
            consumers[cid]["email"] = args["email"]
        return consumers[cid], 200

    def delete(self, cid):                           # DELETE /consumer/<id>
        if consumers.pop(cid, None) is None:
            return {"error": "Consumer not found"}, 404
        return {"message": "Consumer {} deleted".format(cid)}, 200


# ==================================================================
#  PRODUCT
# ==================================================================
class ProductList(Resource):
    def get(self):                                   # GET /product -> all
        return list(products.values()), 200

    def post(self):                                  # POST /product -> create
        parser = reqparse.RequestParser()
        parser.add_argument("name", required=True)
        parser.add_argument("price", type=int, required=True)
        args = parser.parse_args()

        nid = next_id("product")
        products[nid] = {"id": nid, "name": args["name"], "price": args["price"]}
        return products[nid], 201


class Product(Resource):
    def get(self, pid):                              # GET /product/<id>
        if pid in products:
            return products[pid], 200
        return {"error": "Product not found"}, 404

    def put(self, pid):                              # PUT /product/<id> -> update
        parser = reqparse.RequestParser()
        parser.add_argument("name")
        parser.add_argument("price", type=int)
        args = parser.parse_args()

        if pid not in products:
            return {"error": "Product not found"}, 404

        if args["name"] is not None:
            products[pid]["name"] = args["name"]
        if args["price"] is not None:
            products[pid]["price"] = args["price"]
        return products[pid], 200

    def delete(self, pid):                           # DELETE /product/<id>
        if products.pop(pid, None) is None:
            return {"error": "Product not found"}, 404
        return {"message": "Product {} deleted".format(pid)}, 200


# ==================================================================
#  ORDER  (references a consumer and a product)
# ==================================================================
class OrderList(Resource):
    def get(self):                                   # GET /order -> all
        return list(orders.values()), 200

    def post(self):                                  # POST /order -> create
        parser = reqparse.RequestParser()
        parser.add_argument("consumer_id", type=int, required=True)
        parser.add_argument("product_id", type=int, required=True)
        parser.add_argument("quantity", type=int, required=True)
        args = parser.parse_args()

        # basic validation that the referenced records exist
        if args["consumer_id"] not in consumers:
            return {"error": "consumer_id does not exist"}, 400
        if args["product_id"] not in products:
            return {"error": "product_id does not exist"}, 400

        nid = next_id("order")
        orders[nid] = {
            "id": nid,
            "consumer_id": args["consumer_id"],
            "product_id": args["product_id"],
            "quantity": args["quantity"],
        }
        return orders[nid], 201


class Order(Resource):
    def get(self, oid):                              # GET /order/<id>
        if oid in orders:
            return orders[oid], 200
        return {"error": "Order not found"}, 404

    def put(self, oid):                              # PUT /order/<id> -> update
        parser = reqparse.RequestParser()
        parser.add_argument("consumer_id", type=int)
        parser.add_argument("product_id", type=int)
        parser.add_argument("quantity", type=int)
        args = parser.parse_args()

        if oid not in orders:
            return {"error": "Order not found"}, 404

        if args["consumer_id"] is not None:
            if args["consumer_id"] not in consumers:
                return {"error": "consumer_id does not exist"}, 400
            orders[oid]["consumer_id"] = args["consumer_id"]
        if args["product_id"] is not None:
            if args["product_id"] not in products:
                return {"error": "product_id does not exist"}, 400
            orders[oid]["product_id"] = args["product_id"]
        if args["quantity"] is not None:
            orders[oid]["quantity"] = args["quantity"]
        return orders[oid], 200

    def delete(self, oid):                           # DELETE /order/<id>
        if orders.pop(oid, None) is None:
            return {"error": "Order not found"}, 404
        return {"message": "Order {} deleted".format(oid)}, 200


# ---------------- helper landing routes ----------------
@app.route('/')
def home():
    return "Endpoints: /consumer, /product, /order  (add /<id> for a single item)"


# ---------------- register resources ----------------
api.add_resource(ConsumerList, "/consumer")
api.add_resource(Consumer,     "/consumer/<int:cid>")

api.add_resource(ProductList,  "/product")
api.add_resource(Product,      "/product/<int:pid>")

api.add_resource(OrderList,    "/order")
api.add_resource(Order,        "/order/<int:oid>")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)


'''
======================= curl test commands =======================

# ---- CONSUMER ----
curl http://localhost:5001/consumer
curl http://localhost:5001/consumer/1
curl -X POST http://localhost:5001/consumer -H "Content-Type: application/json" -d "{\"name\":\"Jass\",\"email\":\"jass@mail.com\"}"
curl -X PUT  http://localhost:5001/consumer/1 -H "Content-Type: application/json" -d "{\"email\":\"new@mail.com\"}"
curl -X DELETE http://localhost:5001/consumer/2

# ---- PRODUCT ----
curl http://localhost:5001/product
curl http://localhost:5001/product/1
curl -X POST http://localhost:5001/product -H "Content-Type: application/json" -d "{\"name\":\"Mouse\",\"price\":50}"
curl -X PUT  http://localhost:5001/product/1 -H "Content-Type: application/json" -d "{\"price\":1200}"
curl -X DELETE http://localhost:5001/product/2

# ---- ORDER ----
curl http://localhost:5001/order
curl http://localhost:5001/order/1
curl -X POST http://localhost:5001/order -H "Content-Type: application/json" -d "{\"consumer_id\":1,\"product_id\":2,\"quantity\":5}"
curl -X PUT  http://localhost:5001/order/1 -H "Content-Type: application/json" -d "{\"quantity\":10}"
curl -X DELETE http://localhost:5001/order/1
==================================================================
'''