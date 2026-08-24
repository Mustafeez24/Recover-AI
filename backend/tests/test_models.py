from datetime import date, datetime

from app.models import (
    Customer,
    FailureCategory,
    FailureReason,
    Payment,
    PaymentMethod,
    PaymentStatus,
    RecoveryCase,
    RecoveryPriority,
    Subscription,
    SubscriptionStatus,
)


def _make_customer(customer_id="cus_00001"):
    return Customer(
        customer_id=customer_id,
        customer_since=date(2024, 1, 1),
        total_successful_payments=0,
        total_failed_payments=0,
        lifetime_value=0,
        created_at=datetime.utcnow(),
    )


def test_customer_model_creation(db_session):
    customer = _make_customer()
    db_session.add(customer)
    db_session.commit()

    fetched = db_session.get(Customer, "cus_00001")
    assert fetched is not None
    assert fetched.customer_id == "cus_00001"
    assert fetched.total_successful_payments == 0
    assert fetched.lifetime_value == 0


def test_subscription_model_creation(db_session):
    customer = _make_customer()
    db_session.add(customer)
    db_session.commit()

    sub = Subscription(
        subscription_id="sub_00001",
        customer_id=customer.customer_id,
        plan="standard",
        amount=599.0,
        status=SubscriptionStatus.ACTIVE,
        next_payment_date=date(2024, 2, 1),
        created_at=datetime(2024, 1, 1),
    )
    db_session.add(sub)
    db_session.commit()

    fetched = db_session.get(Subscription, "sub_00001")
    assert fetched.plan == "standard"
    assert fetched.status == SubscriptionStatus.ACTIVE


def test_payment_model_creation(db_session):
    customer = _make_customer()
    db_session.add(customer)
    db_session.commit()

    payment = Payment(
        payment_id="pay_00001",
        customer_id=customer.customer_id,
        subscription_id=None,
        amount=499.0,
        currency="INR",
        payment_status=PaymentStatus.SUCCESS,
        failure_reason=None,
        payment_method=PaymentMethod.CARD,
        created_at=datetime(2024, 1, 5),
        retry_count=0,
    )
    db_session.add(payment)
    db_session.commit()

    fetched = db_session.get(Payment, "pay_00001")
    assert fetched.payment_status == PaymentStatus.SUCCESS
    assert fetched.payment_method == PaymentMethod.CARD
    assert fetched.subscription_id is None


def test_recovery_case_model_creation(db_session):
    customer = _make_customer()
    db_session.add(customer)
    db_session.commit()

    payment = Payment(
        payment_id="pay_00002",
        customer_id=customer.customer_id,
        subscription_id=None,
        amount=499.0,
        currency="INR",
        payment_status=PaymentStatus.FAILED,
        failure_reason=FailureReason.INSUFFICIENT_FUNDS,
        payment_method=PaymentMethod.UPI,
        created_at=datetime(2024, 1, 5),
        retry_count=1,
    )
    db_session.add(payment)
    db_session.commit()

    case = RecoveryCase(
        recovery_case_id="rec_00001",
        payment_id=payment.payment_id,
        customer_id=customer.customer_id,
        status="open",
        priority=RecoveryPriority.MEDIUM,
        amount_at_risk=499.0,
        customer_value=0,
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        detection_reason="test reason",
        recommended_next_step="send_payment_reminder",
        created_at=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()

    fetched = db_session.get(RecoveryCase, "rec_00001")
    assert fetched.status == "open"
    assert fetched.payment_id == "pay_00002"


def test_customer_payment_relationship(db_session):
    customer = _make_customer()
    db_session.add(customer)
    db_session.commit()

    payment = Payment(
        payment_id="pay_00003",
        customer_id=customer.customer_id,
        subscription_id=None,
        amount=100.0,
        currency="INR",
        payment_status=PaymentStatus.SUCCESS,
        failure_reason=None,
        payment_method=PaymentMethod.CARD,
        created_at=datetime(2024, 1, 1),
        retry_count=0,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(customer)

    assert len(customer.payments) == 1
    assert customer.payments[0].payment_id == "pay_00003"
    assert payment.customer.customer_id == customer.customer_id


def test_subscription_payment_relationship(db_session):
    customer = _make_customer()
    db_session.add(customer)
    db_session.commit()

    sub = Subscription(
        subscription_id="sub_00002",
        customer_id=customer.customer_id,
        plan="pro",
        amount=1299.0,
        status=SubscriptionStatus.PAST_DUE,
        next_payment_date=None,
        created_at=datetime(2024, 1, 1),
    )
    db_session.add(sub)
    db_session.commit()

    payment = Payment(
        payment_id="pay_00004",
        customer_id=customer.customer_id,
        subscription_id=sub.subscription_id,
        amount=1299.0,
        currency="INR",
        payment_status=PaymentStatus.FAILED,
        failure_reason=FailureReason.BANK_DECLINED,
        payment_method=PaymentMethod.NETBANKING,
        created_at=datetime(2024, 2, 1),
        retry_count=2,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(sub)

    assert len(sub.payments) == 1
    assert sub.payments[0].payment_id == "pay_00004"
    assert payment.subscription.subscription_id == sub.subscription_id


def test_payment_recovery_case_relationship(db_session):
    customer = _make_customer()
    db_session.add(customer)
    db_session.commit()

    payment = Payment(
        payment_id="pay_00005",
        customer_id=customer.customer_id,
        subscription_id=None,
        amount=250.0,
        currency="INR",
        payment_status=PaymentStatus.TIMEOUT,
        failure_reason=FailureReason.TIMEOUT,
        payment_method=None,
        created_at=datetime(2024, 3, 1),
        retry_count=1,
    )
    db_session.add(payment)
    db_session.commit()

    case = RecoveryCase(
        recovery_case_id="rec_00002",
        payment_id=payment.payment_id,
        customer_id=customer.customer_id,
        status="open",
        priority=RecoveryPriority.LOW,
        amount_at_risk=250.0,
        customer_value=0,
        failure_category=FailureCategory.PAYMENT_TIMEOUT,
        detection_reason="test reason",
        recommended_next_step="retry_payment",
        created_at=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(payment)

    assert payment.recovery_case is not None
    assert payment.recovery_case.recovery_case_id == "rec_00002"
    assert case.customer.customer_id == customer.customer_id
