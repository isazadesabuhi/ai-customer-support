"""Fictional support conversations for Ternwick Circuit Supply."""

from dataclasses import dataclass

from support.models import (
    AnalysisCategory,
    ConversationStatus,
    MessageSender,
    Sentiment,
    Urgency,
)

COMPANY_NAME = "Ternwick Circuit Supply"


@dataclass(frozen=True, slots=True)
class SampleCustomer:
    key: str
    name: str
    email: str


@dataclass(frozen=True, slots=True)
class Scenario:
    key: str
    customer_key: str
    subject: str
    status: ConversationStatus
    category: AnalysisCategory
    sentiment: Sentiment
    urgency: Urgency
    messages: tuple[tuple[int, MessageSender, str], ...]


CUSTOMERS = (
    SampleCustomer("rowan", "Rowan Pellwick", "rowan.pellwick@example.com"),
    SampleCustomer("mira", "Mira Fenvale", "mira.fenvale@example.com"),
    SampleCustomer("tess", "Tess Alderfen", "tess.alderfen@example.com"),
    SampleCustomer("dorian", "Dorian Quillmere", "dorian.quillmere@example.com"),
    SampleCustomer("noor", "Noor Brackenby", "noor.brackenby@example.com"),
    SampleCustomer("elio", "Elio Flintmere", "elio.flintmere@example.com"),
    SampleCustomer("inez", "Inez Copperby", "inez.copperby@example.com"),
    SampleCustomer("samir", "Samir Vellbrook", "samir.vellbrook@example.com"),
)

CUSTOMER = MessageSender.CUSTOMER
AGENT = MessageSender.AGENT

SCENARIOS = (
    Scenario(
        "shipping-tracking",
        "rowan",
        "Headphone tracking has stalled",
        ConversationStatus.OPEN,
        AnalysisCategory.SHIPPING,
        Sentiment.NEGATIVE,
        Urgency.HIGH,
        (
            (
                0,
                CUSTOMER,
                "The tracking for order TC-101 has said label created for three days. I need the Mosswave headphones for a train trip tomorrow morning. Can you confirm whether they actually left the warehouse?",
            ),
            (
                25,
                AGENT,
                "The parcel missed its first carrier scan. I am checking whether it was included in yesterday's pickup.",
            ),
            (
                140,
                CUSTOMER,
                "I leave at seven tomorrow. If it has missed dispatch, could you tell me this afternoon so I can make another plan?",
            ),
        ),
    ),
    Scenario(
        "shipping-missing",
        "mira",
        "Delivery scan but no parcel",
        ConversationStatus.PENDING,
        AnalysisCategory.SHIPPING,
        Sentiment.NEGATIVE,
        Urgency.NORMAL,
        (
            (
                0,
                CUSTOMER,
                "My TC-102 cable pouch shows delivered, but the parcel locker is empty.",
            ),
            (
                35,
                AGENT,
                "I can open a carrier trace. Was there a locker notification in your order history?",
            ),
            (
                70,
                CUSTOMER,
                "There is a delivery notification, but it has no locker number.",
            ),
            (
                100,
                AGENT,
                "Could you confirm whether the building reception checked its overflow shelf? I will add that detail to the trace.",
            ),
        ),
    ),
    Scenario(
        "shipping-slot",
        "tess",
        "Change delivery day for speaker",
        ConversationStatus.RESOLVED,
        AnalysisCategory.SHIPPING,
        Sentiment.POSITIVE,
        Urgency.NORMAL,
        (
            (
                0,
                CUSTOMER,
                "Could you move delivery of my Pebblecord speaker to Friday? Thanks for being flexible.",
            ),
            (
                40,
                CUSTOMER,
                "Friday is confirmed on my side. I appreciate you checking before dispatch.",
            ),
            (
                73,
                AGENT,
                "Friday is now booked. The updated delivery date is visible on the order page.",
            ),
        ),
    ),
    Scenario(
        "refund-delay",
        "dorian",
        "Refund overdue after return",
        ConversationStatus.PENDING,
        AnalysisCategory.REFUND,
        Sentiment.NEGATIVE,
        Urgency.NORMAL,
        (
            (
                0,
                CUSTOMER,
                "I sent back the faulty desk charger last week. Order TC-104 still shows no refund and I am frustrated that I have had to chase it twice.",
            ),
            (
                43,
                CUSTOMER,
                "The parcel tracker shows it arrived at your returns desk four days ago.",
            ),
            (
                81,
                AGENT,
                "I will ask the returns desk to match the parcel to the order. Could you confirm the date shown in your return confirmation?",
            ),
        ),
    ),
    Scenario(
        "refund-accessory",
        "noor",
        "Refund for an incorrect adapter",
        ConversationStatus.RESOLVED,
        AnalysisCategory.REFUND,
        Sentiment.POSITIVE,
        Urgency.NORMAL,
        (
            (
                0,
                CUSTOMER,
                "The parcel contained a short adapter instead of the right-angle adapter I ordered. A refund would work for me.",
            ),
            (
                34,
                AGENT,
                "I found the picking error and approved the refund for the adapter.",
            ),
            (
                162,
                CUSTOMER,
                "I see the refund confirmation in my account. Thanks for sorting that out so quickly.",
            ),
            (
                210,
                AGENT,
                "Glad that is sorted. I have updated the order with the refund confirmation.",
            ),
        ),
    ),
    Scenario(
        "refund-return",
        "elio",
        "Return delivered, refund timing question",
        ConversationStatus.OPEN,
        AnalysisCategory.REFUND,
        Sentiment.NEUTRAL,
        Urgency.NORMAL,
        (
            (
                0,
                CUSTOMER,
                "The return for my unused desk hub shows received this morning. When should I expect the refund confirmation for TC-106?",
            ),
        ),
    ),
    Scenario(
        "billing-duplicate",
        "inez",
        "Two entries for one order",
        ConversationStatus.PENDING,
        AnalysisCategory.BILLING,
        Sentiment.NEGATIVE,
        Urgency.NORMAL,
        (
            (
                0,
                CUSTOMER,
                "My statement shows two charges for order TC-107, but I only bought one charger. I want to know why I have been billed twice.",
            ),
            (
                24,
                CUSTOMER,
                "Both entries appeared the same afternoon. Only one receipt is in the shop.",
            ),
            (
                50,
                AGENT,
                "I can see one completed order. Could you tell me whether both entries are posted or whether one is still marked pending?",
            ),
        ),
    ),
    Scenario(
        "billing-invoice",
        "samir",
        "Correct invoice before expense cutoff",
        ConversationStatus.RESOLVED,
        AnalysisCategory.BILLING,
        Sentiment.POSITIVE,
        Urgency.HIGH,
        (
            (
                0,
                CUSTOMER,
                "The expense portal closes at noon today. Could you issue the invoice for TC-108 with the shop's itemized amounts? The summary receipt was rejected.",
            ),
            (
                20,
                AGENT,
                "I replaced the summary with an itemized invoice in the order history.",
            ),
            (
                45,
                CUSTOMER,
                "That worked and I submitted it before the cutoff. Thank you.",
            ),
            (
                60,
                AGENT,
                "You are welcome. The corrected copy will stay available in the order history.",
            ),
        ),
    ),
    Scenario(
        "billing-discount",
        "rowan",
        "Bundle price differs at checkout",
        ConversationStatus.OPEN,
        AnalysisCategory.BILLING,
        Sentiment.NEUTRAL,
        Urgency.NORMAL,
        (
            (
                0,
                CUSTOMER,
                "The desk bundle page shows a lower price than my checkout total. Is the bundle discount applied after I choose a delivery option?",
            ),
            (
                48,
                AGENT,
                "The discount should show before checkout. Which items are currently in the bundle?",
            ),
            (
                130,
                CUSTOMER,
                "It is the Corkline desk mat with the Mosswave stand. I selected both from the bundle page.",
            ),
        ),
    ),
    Scenario(
        "product-keyboard",
        "mira",
        "Keyboard compatibility with Linux",
        ConversationStatus.RESOLVED,
        AnalysisCategory.PRODUCT,
        Sentiment.NEUTRAL,
        Urgency.LOW,
        (
            (
                0,
                CUSTOMER,
                "Does the Alderkey K2 wireless keyboard work on Linux via Bluetooth, including the basic media keys?",
            ),
            (
                33,
                CUSTOMER,
                "I only need standard key input and volume controls. I can skip the companion app.",
            ),
            (
                66,
                AGENT,
                "The K2 pairs as a standard Bluetooth keyboard on Linux. Volume keys use standard controls. The lighting app is optional.",
            ),
        ),
    ),
    Scenario(
        "product-monitor",
        "tess",
        "Display adapter needed before a workshop",
        ConversationStatus.OPEN,
        AnalysisCategory.PRODUCT,
        Sentiment.NEUTRAL,
        Urgency.HIGH,
        (
            (
                0,
                CUSTOMER,
                "I am presenting at a workshop this afternoon. Will the Ridgeport M2 drive an HDMI projector from a laptop USB-C port? I have time to collect one before the session.",
            ),
            (
                19,
                AGENT,
                "It will if the laptop's USB-C port supports display output. Does the port have a display symbol?",
            ),
            (
                35,
                CUSTOMER,
                "Yes, there is a display symbol by the port. Could you confirm the M2 includes the HDMI lead before I leave for collection?",
            ),
        ),
    ),
    Scenario(
        "product-headset",
        "dorian",
        "Headset microphone support",
        ConversationStatus.OPEN,
        AnalysisCategory.PRODUCT,
        Sentiment.NEUTRAL,
        Urgency.LOW,
        (
            (
                0,
                CUSTOMER,
                "Does the Bramblewave H1 microphone work when plugged into a laptop with a single combination audio jack?",
            ),
        ),
    ),
    Scenario(
        "account-lockout",
        "noor",
        "Cannot sign in after changing password",
        ConversationStatus.PENDING,
        AnalysisCategory.ACCOUNT,
        Sentiment.NEGATIVE,
        Urgency.HIGH,
        (
            (
                0,
                CUSTOMER,
                "I changed my shop password yesterday and now sign-in keeps looping. I need to confirm a collection before the desk closes at five.",
            ),
            (
                22,
                AGENT,
                "Please try the sign-in page in a private browser window. Let me know which error appears after you submit.",
            ),
            (
                59,
                CUSTOMER,
                "It still loops back to the sign-in screen without showing an error.",
            ),
            (
                88,
                AGENT,
                "Which browser and device are you using? I can check whether the issue affects that combination.",
            ),
        ),
    ),
    Scenario(
        "account-notices",
        "elio",
        "Order notifications are paused",
        ConversationStatus.CLOSED,
        AnalysisCategory.ACCOUNT,
        Sentiment.POSITIVE,
        Urgency.LOW,
        (
            (
                0,
                CUSTOMER,
                "Thanks for getting back to me. Where can I turn order updates back on for my account?",
            ),
            (
                52,
                AGENT,
                "Open Account Preferences and switch Order Updates on. Marketing preferences are managed separately.",
            ),
            (
                230,
                CUSTOMER,
                "Found it and received my delivery update. You can close this one. Thanks!",
            ),
        ),
    ),
    Scenario(
        "general-hours",
        "inez",
        "Weekend support hours",
        ConversationStatus.CLOSED,
        AnalysisCategory.GENERAL,
        Sentiment.POSITIVE,
        Urgency.LOW,
        (
            (
                0,
                CUSTOMER,
                "Hello! Could you share your weekend support hours? Your team was really helpful last time.",
            ),
            (
                65,
                AGENT,
                "We answer messages on Saturday from ten to four. Sunday messages are picked up on Monday.",
            ),
        ),
    ),
    Scenario(
        "general-policy",
        "samir",
        "Standard return window for gifts",
        ConversationStatus.RESOLVED,
        AnalysisCategory.GENERAL,
        Sentiment.NEUTRAL,
        Urgency.LOW,
        (
            (
                0,
                CUSTOMER,
                "What is the usual return window if I am buying an accessory as a gift?",
            ),
            (
                72,
                CUSTOMER,
                "It would stay unopened until the recipient tries it next week.",
            ),
            (
                110,
                AGENT,
                "For our standard policy, the return window is thirty days from delivery. Keep the order reference so we can locate the purchase.",
            ),
        ),
    ),
    Scenario(
        "other-cartons",
        "rowan",
        "Empty cartons for a community workshop",
        ConversationStatus.CLOSED,
        AnalysisCategory.OTHER,
        Sentiment.NEUTRAL,
        Urgency.LOW,
        (
            (
                0,
                CUSTOMER,
                "My community repair club is making a packaging display. Could we collect a few clean empty display cartons from your shop?",
            ),
            (
                180,
                AGENT,
                "We send display cartons into our recycling stream, so none are available for collection.",
            ),
            (
                350,
                CUSTOMER,
                "Understood. We will make our own display boxes. Thanks for checking.",
            ),
        ),
    ),
    Scenario(
        "other-exhibit",
        "mira",
        "Permission to show a retired shop display",
        ConversationStatus.OPEN,
        AnalysisCategory.OTHER,
        Sentiment.NEUTRAL,
        Urgency.LOW,
        (
            (
                0,
                CUSTOMER,
                "Our library is exhibiting local retail design. Could we display a photo of your retired counter sign alongside a short credit?",
            ),
            (
                240,
                AGENT,
                "I can route your request. Is the photo only for the physical display or also for an online catalogue?",
            ),
            (
                900,
                CUSTOMER,
                "Just the printed panel in the library. We can share a draft caption if that helps.",
            ),
        ),
    ),
)
