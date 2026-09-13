'''
REST API: E-Commerce Product Pricing & Multi-Currency Versioning with Caching

The real-life story:
    v1 launched assuming a single default currency with a flat integer `price`:
        v1 product -> { id, name, price }   (e.g., price: 1000)

    Later, global expansion required explicit multi-currency pricing, handling
    cents/minor subunits to avoid floating-point errors:
        v2 product -> { id, name, pricing: { amount, currency, precision } }

    Both versions share the canonical multi-currency data store.
    Flask-Caching is integrated with cross-version cache purging on mutations.

Routes:
    v1: /api/v1/product  (+ /<id>)
    v2: /api/v2/product  (+ /<id>)
    consumer and order endpoints remain available for parity.

Run: python rest_api.py (serves on http://localhost:5001)
'''

from flask import Flask, request
from flask_restful import Api, Resource, reqparse
from flask_caching import Cache

app = Flask(__name__)
api = Api(app)

# ==================================================================
#  CACHE SETUP
# ==================================================================
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Default: 5 minutes
cache = Cache(app)

# Explicit cache key based on request path
def make_cache_key(*args, **kwargs):
    return f"view_{request.path}"

# Only cache successful 200 responses, preventing 404 caching
response_filter_200 = lambda resp: resp[1] == 200 if isinstance(resp, tuple) else True

# ==================================================================
#  DATA STORE (Canonical v2 multi-currency structure)
# ==================================================================
# Amounts stored in minor currency units (cents/pence) with precision metadata
products = {
    1: {
        "id": 1,
        "name": "Laptop",
        "pricing": {"amount": 100000, "currency": "USD", "precision": 2}  # $1000.00
    },
    2: {
        "id": 2,
        "name": "Phone",
        "pricing": {"amount": 50000, "currency": "USD", "precision": 2}   # $500.00
    },
}

consumers = {
    1: {"id": 1, "name": "Nicholas Cage", "email": "nick@mail.com"},
    2: {"id": 2, "name": "Elvin Doe", "email": "elvin@mail.com"},
}

orders = {
    1: {"id": 1, "consumer_id": 1, "product_id": 2, "quantity": 3},
}

counters = {"consumer": 3, "product": 3, "order": 2}


def next_id(kind):
    nid = counters[kind]
    counters[kind] += 1
    return nid


# ==================================================================
#  CACHE INVALIDATION HELPERS
# ==================================================================
def invalidate_consumer_cache(cid=None):
    cache.delete("view_/api/v1/consumer")
    cache.delete("view_/api/v2/consumer")
    if cid:
        cache.delete(f"view_/api/v1/consumer/{cid}")
        cache.delete(f"view_/api/v2/consumer/{cid}")


def invalidate_product_cache(pid=None):
    # Invalidate collection endpoints for both API versions
    cache.delete("view_/api/v1/product")
    cache.delete("view_/api/v2/product")
    # Invalidate specific entity caches if an ID is provided
    if pid:
        cache.delete(f"view_/api/v1/product/{pid}")
        cache.delete(f"view_/api/v2/product/{pid}")


def invalidate_order_cache(oid=None):
    cache.delete("view_/api/v1/order")
    cache.delete("view_/api/v2/order")
    if oid:
        cache.delete(f"view_/api/v1/order/{oid}")
        cache.delete(f"view_/api/v2/order/{oid}")


# ==================================================================
#  CONSUMER (Full CRUD + Caching)
# ==================================================================
class ConsumerList(Resource):
    @cache.cached(timeout=120, make_cache_key=make_cache_key, response_filter=response_filter_200)
    def get(self):
        # GET /api/v1/consumer OR /api/v2/consumer
        return list(consumers.values()), 200

    def post(self):
        # POST /api/v1/consumer OR /api/v2/consumer
        parser = reqparse.RequestParser()
        parser.add_argument("name", required=True, help="name is required")
        parser.add_argument("email", required=True, help="email is required")
        args = parser.parse_args()

        nid = next_id("consumer")
        consumers[nid] = {
            "id": nid,
            "name": args["name"],
            "email": args["email"]
        }
        invalidate_consumer_cache()
        return consumers[nid], 201


class Consumer(Resource):
    @cache.cached(timeout=120, make_cache_key=make_cache_key, response_filter=response_filter_200)
    def get(self, cid):
        # GET /api/v1/consumer/<cid> OR /api/v2/consumer/<cid>
        if cid not in consumers:
            return {"error": "Consumer not found"}, 404
        return consumers[cid], 200

    def put(self, cid):
        # PUT /api/v1/consumer/<cid> OR /api/v2/consumer/<cid>
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

        invalidate_consumer_cache(cid)
        return consumers[cid], 200

    def delete(self, cid):
        # DELETE /api/v1/consumer/<cid> OR /api/v2/consumer/<cid>
        if consumers.pop(cid, None) is None:
            return {"error": "Consumer not found"}, 404

        invalidate_consumer_cache(cid)
        return {"message": f"Consumer {cid} deleted"}, 200


# ==================================================================
#  PRODUCT SERIALIZERS / VIEW ADAPTERS
# ==================================================================
def product_v1_view(p):
    # v1 contract: convert subunit minor units to standard major integer price
    pricing = p["pricing"]
    divisor = 10 ** pricing.get("precision", 2)
    major_price = int(pricing["amount"] / divisor)
    return {
        "id": p["id"],
        "name": p["name"],
        "price": major_price
    }


def product_v2_view(p):
    # v2 contract: return complete explicit currency object
    return {
        "id": p["id"],
        "name": p["name"],
        "pricing": {
            "amount": p["pricing"]["amount"],
            "currency": p["pricing"]["currency"],
            "precision": p["pricing"]["precision"]
        }
    }


# ==================================================================
#  PRODUCT v1 RESOURCES (Legacy Flat Pricing)
# ==================================================================
class ProductListV1(Resource):
    @cache.cached(timeout=300, make_cache_key=make_cache_key, response_filter=response_filter_200)
    def get(self):
        return [product_v1_view(p) for p in products.values()], 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("name", required=True)
        parser.add_argument("price", type=int, required=True)
        args = parser.parse_args()

        nid = next_id("product")
        # Store in canonical v2 structure (assume default USD, 2 decimal places)
        products[nid] = {
            "id": nid,
            "name": args["name"],
            "pricing": {
                "amount": args["price"] * 100,
                "currency": "USD",
                "precision": 2
            }
        }
        invalidate_product_cache()
        return product_v1_view(products[nid]), 201


class ProductV1(Resource):
    @cache.cached(timeout=300, make_cache_key=make_cache_key, response_filter=response_filter_200)
    def get(self, pid):
        print(f"--> [DATABASE QUERY] Fetching Product {pid} from memory store")
        if pid not in products:
            return {"error": "Product not found"}, 404
        return product_v1_view(products[pid]), 200

    def put(self, pid):
        parser = reqparse.RequestParser()
        parser.add_argument("name")
        parser.add_argument("price", type=int)
        args = parser.parse_args()

        if pid not in products:
            return {"error": "Product not found"}, 404

        if args["name"] is not None:
            products[pid]["name"] = args["name"]
        if args["price"] is not None:
            products[pid]["pricing"]["amount"] = args["price"] * 100

        invalidate_product_cache(pid)
        return product_v1_view(products[pid]), 200

    def delete(self, pid):
        if products.pop(pid, None) is None:
            return {"error": "Product not found"}, 404
        invalidate_product_cache(pid)
        return {"message": f"Product {pid} deleted"}, 200


# ==================================================================
#  PRODUCT v2 RESOURCES (Structured Multi-Currency)
# ==================================================================
class ProductListV2(Resource):
    @cache.cached(timeout=300, make_cache_key=make_cache_key, response_filter=response_filter_200)
    def get(self):
        return [product_v2_view(p) for p in products.values()], 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("name", required=True)
        parser.add_argument("amount", type=int, required=True, location='json')
        parser.add_argument("currency", type=str, required=True, location='json')
        parser.add_argument("precision", type=int, default=2, location='json')
        args = parser.parse_args()

        nid = next_id("product")
        products[nid] = {
            "id": nid,
            "name": args["name"],
            "pricing": {
                "amount": args["amount"],
                "currency": args["currency"].upper(),
                "precision": args["precision"]
            }
        }
        invalidate_product_cache()
        return product_v2_view(products[nid]), 201


class ProductV2(Resource):
    @cache.cached(timeout=300, make_cache_key=make_cache_key, response_filter=response_filter_200)
    def get(self, pid):
        if pid not in products:
            return {"error": "Product not found"}, 404
        return product_v2_view(products[pid]), 200

    def put(self, pid):
        parser = reqparse.RequestParser()
        parser.add_argument("name")
        parser.add_argument("amount", type=int, location='json')
        parser.add_argument("currency", type=str, location='json')
        parser.add_argument("precision", type=int, location='json')
        args = parser.parse_args()

        if pid not in products:
            return {"error": "Product not found"}, 404

        if args["name"] is not None:
            products[pid]["name"] = args["name"]
        if args["amount"] is not None:
            products[pid]["pricing"]["amount"] = args["amount"]
        if args["currency"] is not None:
            products[pid]["pricing"]["currency"] = args["currency"].upper()
        if args["precision"] is not None:
            products[pid]["pricing"]["precision"] = args["precision"]

        invalidate_product_cache(pid)
        return product_v2_view(products[pid]), 200

    def delete(self, pid):
        if products.pop(pid, None) is None:
            return {"error": "Product not found"}, 404
        invalidate_product_cache(pid)
        return {"message": f"Product {pid} deleted"}, 200
    

# ==================================================================
#  ORDER
# ==================================================================
class OrderList(Resource):
    @cache.cached(timeout=30, make_cache_key=make_cache_key, response_filter=response_filter_200)
    def get(self):
        return list(orders.values()), 200

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("consumer_id", type=int, required=True)
        parser.add_argument("product_id", type=int, required=True)
        parser.add_argument("quantity", type=int, required=True)
        args = parser.parse_args()

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
        invalidate_order_cache()
        return orders[nid], 201


class Order(Resource):
    @cache.cached(timeout=60, make_cache_key=make_cache_key, response_filter=response_filter_200)
    def get(self, oid):
        if oid in orders:
            return orders[oid], 200
        return {"error": "Order not found"}, 404


# ---------------- landing route ----------------
@app.route('/')
def home():
    return (
        "Multi-Currency Versioned Product API Active:<br>"
        "v1 Product -> {id, name, price}<br>"
        "v2 Product -> {id, name, pricing: {amount, currency, precision}}<br>"
        "Try /api/v1/product/1 vs /api/v2/product/1"
    )


# ---------------- register resources ----------------
# PRODUCT: Version-specific resources
api.add_resource(ProductListV1, "/api/v1/product")
api.add_resource(ProductV1,     "/api/v1/product/<int:pid>")
api.add_resource(ProductListV2, "/api/v2/product")
api.add_resource(ProductV2,     "/api/v2/product/<int:pid>")

# CONSUMER & ORDER: Unversioned parity routes
api.add_resource(ConsumerList, "/api/v1/consumer", "/api/v2/consumer")
api.add_resource(Consumer,     "/api/v1/consumer/<int:cid>", "/api/v2/consumer/<int:cid>")
api.add_resource(OrderList,    "/api/v1/order", "/api/v2/order")
api.add_resource(Order,        "/api/v1/order/<int:oid>", "/api/v2/order/<int:oid>")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)