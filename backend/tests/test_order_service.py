from sqlmodel import Session, SQLModel, create_engine

from app.models.product import Product
from app.services.order_service import OrderService


def create_test_db():

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False}
    )

    SQLModel.metadata.create_all(engine)

    return engine


def seed_product(session):

    product = Product(
        id="shoe_001",
        name="Air Runner Black",
        category="shoes",
        price=2199,
        currency="INR",
        stock=12,
        attributes={
            "color": "black",
            "size": [7, 8, 9, 10],
        },
    )

    session.add(product)
    session.commit()


def test_create_order():

    engine = create_test_db()

    with Session(engine) as session:

        seed_product(session)

        service = OrderService(session)

        order = service.create_order(
            item_id="shoe_001",
            qty=2,
            selected_attributes={
                "size": 9
            },
        )

        assert order.item_id == "shoe_001"
        assert order.qty == 2
        assert order.amount == 4398
        assert order.status == "pending_payment"
        assert order.selected_attributes == {
            "size": 9
        }


def test_invalid_attribute():

    engine = create_test_db()

    with Session(engine) as session:

        seed_product(session)

        service = OrderService(session)

        try:

            service.create_order(
                item_id="shoe_001",
                qty=1,
                selected_attributes={
                    "size": 15
                },
            )

            assert False

        except ValueError:
            assert True