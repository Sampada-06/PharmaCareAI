import re
from typing import Optional, Literal
from pydantic import BaseModel

class AgentIntent(BaseModel):
    intent: str
    medicine_name: Optional[str] = None
    quantity: Optional[int] = 1
    requires_prescription_check: bool = False
    user_message_summary: Optional[str] = None

def extract_intent_regex(message: str) -> Optional[AgentIntent]:
    msg = message.lower().strip()
    
    # 1. ADD TO CART: "add 5 paracetamol 500mg", "add crocin to cart"
    add_match = re.search(r'\badd\b\s*(?:(\d+)\s+)?(.*?)(?:\s+to\s+cart|\s+to\s+my\s+cart|$)', msg)
    if add_match and len(add_match.group(2).strip()) > 2:
        qty_str = add_match.group(1)
        qty = int(qty_str) if qty_str else 1
        med_name = add_match.group(2).strip()
        return AgentIntent(
            intent="add_to_cart",
            medicine_name=med_name.title(),
            quantity=qty,
            requires_prescription_check=True,
            user_message_summary=f"Regex: Add {qty} {med_name}"
        )

    # 2. CHECK STOCK
    check_match = re.search(r'\b(?:check|is|do you have|available|stock)\b\s*(.*?)\s*(?:\bavailable\b|\bstock\b|\bin stock\b|\bavailable\b|$)', msg)
    if check_match and len(check_match.group(1).strip()) > 2:
        med_name = check_match.group(1).strip()
        med_name = re.sub(r'^(?:is|check|for|has|got)\s+', '', med_name)
        return AgentIntent(
            intent="check_stock",
            medicine_name=med_name.title(),
            quantity=1,
            user_message_summary=f"Regex: Check stock for {med_name}"
        )

    return None

def test():
    msgs = [
        "add 5 Torrent Paracetamol 500mg",
        "add crocin to cart",
        "is aspirin available?",
        "check stock for vicks",
        "add 1 paracetamol",
        "hello"
    ]
    
    for m in msgs:
        intent = extract_intent_regex(m)
        print(f"Input: '{m}' -> Intent: {intent.intent if intent else 'None'}")
        if intent:
            print(f"   Med: {intent.medicine_name}, Qty: {intent.quantity}")

if __name__ == "__main__":
    test()
