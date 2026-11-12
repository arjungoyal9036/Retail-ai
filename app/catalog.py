from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    category: str
    description: str
    price: float
    tags: tuple[str, ...]
    popularity: int


PRODUCTS = (
    Product(
        "p-1001",
        "Everyday Canvas Backpack",
        "bags",
        "A lightweight canvas backpack for commuting and weekend trips.",
        49.00,
        ("canvas", "travel", "everyday", "casual"),
        92,
    ),
    Product(
        "p-1002",
        "Trailbound Hiking Pack",
        "bags",
        "A weather-resistant day pack with supportive straps and trail storage.",
        89.00,
        ("hiking", "travel", "outdoors", "water-resistant"),
        85,
    ),
    Product(
        "p-1003",
        "Minimal Leather Crossbody",
        "bags",
        "A compact crossbody bag with a clean design for daily essentials.",
        74.00,
        ("leather", "everyday", "minimal", "accessories"),
        78,
    ),
    Product(
        "p-2001",
        "Cloud Knit Sweater",
        "clothing",
        "A soft, relaxed-fit knit sweater for cool-weather layering.",
        68.00,
        ("knit", "warm", "casual", "winter"),
        96,
    ),
    Product(
        "p-2002",
        "Classic Cotton T-Shirt",
        "clothing",
        "A breathable cotton tee designed for comfortable everyday wear.",
        24.00,
        ("cotton", "basics", "casual", "everyday"),
        99,
    ),
    Product(
        "p-2003",
        "All-Weather Running Jacket",
        "clothing",
        "A lightweight jacket with a water-resistant finish for outdoor runs.",
        112.00,
        ("running", "outdoors", "water-resistant", "activewear"),
        82,
    ),
    Product(
        "p-3001",
        "Insulated Travel Tumbler",
        "home",
        "A reusable tumbler that keeps drinks hot or cold while you travel.",
        32.00,
        ("travel", "reusable", "coffee", "everyday"),
        94,
    ),
    Product(
        "p-3002",
        "Stoneware Pour-Over Set",
        "home",
        "A handmade-style ceramic dripper and mug set for slow coffee mornings.",
        56.00,
        ("coffee", "ceramic", "kitchen", "gift"),
        73,
    ),
    Product(
        "p-3003",
        "Soft Cotton Throw",
        "home",
        "A cozy, machine-washable throw blanket for the sofa or bedroom.",
        64.00,
        ("cotton", "home", "cozy", "gift"),
        80,
    ),
    Product(
        "p-4001",
        "Wireless Studio Headphones",
        "electronics",
        "Comfortable over-ear headphones with clear sound for work or travel.",
        129.00,
        ("wireless", "audio", "work", "travel"),
        91,
    ),
    Product(
        "p-4002",
        "Compact Bluetooth Speaker",
        "electronics",
        "A portable speaker with room-filling sound for home and outdoors.",
        59.00,
        ("wireless", "audio", "portable", "outdoors"),
        87,
    ),
    Product(
        "p-4003",
        "USB-C Desk Lamp",
        "electronics",
        "An adjustable LED desk lamp with warm and cool light settings.",
        45.00,
        ("lighting", "desk", "work", "home"),
        76,
    ),
)

PRODUCT_BY_ID = {product.id: product for product in PRODUCTS}


def product_as_dict(product: Product) -> dict[str, object]:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "description": product.description,
        "price": product.price,
        "tags": list(product.tags),
        "popularity": product.popularity,
    }


def product_from_dict(data: dict[str, object]) -> Product:
    return Product(
        id=str(data["id"]),
        name=str(data["name"]),
        category=str(data["category"]),
        description=str(data["description"]),
        price=float(data["price"]),
        tags=tuple(str(tag) for tag in data["tags"]),
        popularity=int(data["popularity"]),
    )


def search_products(
    query: str,
    limit: int = 5,
    *,
    products: tuple[Product, ...] | list[Product] = PRODUCTS,
) -> list[Product]:
    terms = set(query.casefold().split())
    if not terms:
        return []

    matches = []
    for product in products:
        searchable_text = " ".join(
            (product.name, product.category, product.description, *product.tags)
        ).casefold()
        score = sum(term in searchable_text for term in terms)
        if score:
            matches.append((score, product.popularity, product))

    matches.sort(key=lambda result: (result[0], result[1]), reverse=True)
    return [product for _, _, product in matches[:limit]]
