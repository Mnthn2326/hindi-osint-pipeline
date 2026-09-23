"""Impact classification pilot test (Phase 6).

Runs zero-shot classification using MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
on 5 hand-picked Hindi text + entity pairs to verify if the model understands
Hindi and produces sensible positive/negative/neutral labels.
"""

from transformers import pipeline


def main() -> None:
    model_name = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
    print(f"Loading zero-shot classification pipeline with {model_name}...")

    try:
        classifier = pipeline("zero-shot-classification", model=model_name)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    pairs = [
        {
            "text": "'भारत की सुनहरी दहाड़': एशियन गेम्स में विमेंस क्रिकेट टीम ने दिलाया पहला गोल्ड, तो लगा बधाईयों का तांता",
            "entity": "भारत",
            "expected_human": "सकारात्मक",  # Positive (India wins gold)
        },
        {
            "text": "पीएम मोदी जाएंगे अमेरिका, दिसंबर में डोनाल्ड ट्रंप से होगी मुलाकात, एजेंडी में क्या-क्या?",
            "entity": "अमेरिका",
            "expected_human": "तटस्थ",  # Neutral (Diplomatic visit)
        },
        {
            "text": "'ECI वाले राजद्रोह कर रहे...टाइम आएगा और हम आपको पकड़ेंगे', चुनाव आयोग पर राहुल गांधी का तीखा हमला",
            "entity": "चुनाव आयोग",
            "expected_human": "नकारात्मक",  # Negative (ECI is attacked/threatened)
        },
        {
            "text": "बंगाल की खाड़ी में बन रहा अर्णब तूफान, 12 घंटे में ढाएगा तबाही! IMD ने जारी किया रेड अलर्ट",
            "entity": "भारत",
            "expected_human": "नकारात्मक",  # Negative (Destructive cyclone hitting country)
        },
        {
            "text": "Indus Water Treaty: सिंधु जल समझौते पर UN पहुंचा पाकिस्तान, भारत ने की ऐसी बेइज्जती, 7 पुस्त तक याद रखेंगे शहबाज",
            "entity": "पाकिस्तान",
            "expected_human": "नकारात्मक",  # Negative (Pakistan insulted/humiliated)
        },
    ]

    candidate_labels = ["सकारात्मक", "नकारात्मक", "तटस्थ"]

    print("\nRunning pilot tests:\n" + "-" * 50)
    correct_count = 0

    for i, p in enumerate(pairs, 1):
        text = p["text"]
        entity = p["entity"]
        expected = p["expected_human"]

        # Formulate hypothesis template based on prompt requirement
        template = f"इस घटना का {entity} पर {{}} प्रभाव है।"

        try:
            result = classifier(text, candidate_labels, hypothesis_template=template)
            best_label = result["labels"][0]
            confidence = result["scores"][0]

            is_match = best_label == expected
            if is_match:
                correct_count += 1

            print(f"Test {i}:")
            print(f"Text:   {text}")
            print(f"Entity: {entity}")
            print(f"Pred:   {best_label} (Conf: {confidence:.2f})")
            print(f"Expect: {expected}")
            print(f"Match?: {'YES' if is_match else 'NO'}")
            print("-" * 50)
        except Exception as e:
            print(f"Test {i} failed during inference: {e}")

    print(f"\nFinal Result: {correct_count}/5 matches with human logic.")
    if correct_count < 3:
        print("WARNING: Model performance is poor. Do not proceed to full pipeline stage.")
    else:
        print("SUCCESS: Model understands Hindi NLI appropriately.")


if __name__ == "__main__":
    main()
