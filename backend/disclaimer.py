"""Product disclaimer — not a medical device; model limitations."""

PRODUCT_DISCLAIMER = {
    "summary": (
        "SnakeBiteRx is educational decision-support software. It is not a medical device, "
        "not FDA/CE cleared, and not a substitute for professional diagnosis or treatment."
    ),
    "model_limitations": (
        "Models can be wrong. Wound images may be misclassified; the app may report "
        "'unknown' when confidence is low. Geographic and symptom priors are statistical "
        "and incomplete. Snake species rankings are estimates, not confirmed identifications."
    ),
    "emergency": (
        "For suspected snakebite, follow local emergency protocols immediately. "
        "Do not delay care because of this app."
    ),
    "ensemble_note": (
        "The wound model combines EfficientNet-B3 (58%), ResNet50 (26%), and DenseNet121 (16%) "
        "softmax outputs by default. When the combined confidence is below 60%, the wound prediction is "
        "treated as uncertain and multimodal fusion relies more on symptoms and geography."
    ),
}
