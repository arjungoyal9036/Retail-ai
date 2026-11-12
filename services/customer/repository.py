from pymongo.collection import Collection


class MongoProfileRepository:
    def __init__(self, collection: Collection) -> None:
        self._collection = collection
        self._collection.create_index("customer_id", unique=True)

    def get_profile(self, customer_id: str) -> dict[str, object] | None:
        return self._collection.find_one({"customer_id": customer_id}, {"_id": False})

    def save_profile(self, profile: dict[str, object]) -> dict[str, object]:
        self._collection.replace_one(
            {"customer_id": profile["customer_id"]},
            profile,
            upsert=True,
        )
        return profile
