"""
Phone number validation logic for Azerbaijan phone numbers
"""
import re
from typing import Optional


class PhoneValidator:
    """Validates Azerbaijan phone numbers before database insertion"""

    # Valid prefixes for Azerbaijan phone numbers (first 2 digits)
    VALID_PREFIXES = ['10', '50', '51', '55', '60', '70', '77', '99']

    # Invalid third digits
    INVALID_THIRD_DIGITS = ['0', '1']

    @staticmethod
    def clean_phone(phone_raw: str) -> str:
        """
        Extract all non-numeric characters and keep only digits

        Args:
            phone_raw: Raw phone number string

        Returns:
            String with only numeric digits
        """
        return re.sub(r'\D', '', phone_raw)

    @staticmethod
    def validate_phone(phone_number: str) -> Optional[str]:
        """
        Validate phone number according to Azerbaijan phone number rules

        Rules:
        1. Extract all non-numeric strings from the number
        2. Take last 9 digits
        3. Length must be 9
        4. First 2 digits should be one of: 10, 50, 51, 55, 60, 70, 77, 99
        5. 3rd digit cannot be 0 or 1

        Args:
            phone_number: Phone number to validate

        Returns:
            Validated 9-digit phone number or None if validation fails
        """
        # Rule 1: Extract only numeric digits
        cleaned = PhoneValidator.clean_phone(phone_number)

        if not cleaned:
            return None

        # Rule 2: Take last 9 digits
        phone_9digit = cleaned[-9:]

        # Rule 3: Length must be exactly 9
        if len(phone_9digit) != 9:
            return None

        # Rule 4: First 2 digits must be valid prefix
        prefix = phone_9digit[:2]
        if prefix not in PhoneValidator.VALID_PREFIXES:
            return None

        # Rule 5: 3rd digit cannot be 0 or 1
        third_digit = phone_9digit[2]
        if third_digit in PhoneValidator.INVALID_THIRD_DIGITS:
            return None

        return phone_9digit

    @staticmethod
    def is_valid(phone_number: str) -> bool:
        """
        Check if phone number is valid

        Args:
            phone_number: Phone number to check

        Returns:
            True if valid, False otherwise
        """
        return PhoneValidator.validate_phone(phone_number) is not None


# Example usage and testing
if __name__ == "__main__":
    test_cases = [
        # Valid cases
        ("994505551234", True, "505551234"),  # Valid with country code
        ("505551234", True, "505551234"),      # Valid 9 digits
        ("0505551234", True, "505551234"),     # Valid with leading 0
        ("+994 50 555 12 34", True, "505551234"),  # Valid with formatting
        ("994555551234", True, "555551234"),   # Valid prefix 55
        ("994705551234", True, "705551234"),   # Valid prefix 70
        ("994775551234", True, "775551234"),   # Valid prefix 77
        ("994995551234", True, "995551234"),   # Valid prefix 99
        ("994105551234", True, "105551234"),   # Valid prefix 10
        ("994515551234", True, "515551234"),   # Valid prefix 51
        ("994605551234", True, "605551234"),   # Valid prefix 60

        # Invalid cases - wrong prefix
        ("994405551234", False, None),         # Invalid prefix 40
        ("994205551234", False, None),         # Invalid prefix 20

        # Invalid cases - 3rd digit is 0 or 1
        ("994500551234", False, None),         # 3rd digit is 0
        ("994501551234", False, None),         # 3rd digit is 1
        ("994550551234", False, None),         # 3rd digit is 0
        ("994551551234", False, None),         # 3rd digit is 1

        # Invalid cases - wrong length
        ("50555123", False, None),             # Only 8 digits
        ("5055512345", False, None),           # 10 digits

        # Invalid cases - no digits
        ("abcdefghi", False, None),            # No numbers
        ("", False, None),                     # Empty string
    ]

    print("Phone Number Validation Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for phone_input, should_be_valid, expected_output in test_cases:
        result = PhoneValidator.validate_phone(phone_input)
        is_valid = result is not None

        if is_valid == should_be_valid and result == expected_output:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1

        print(f"{status} | Input: {phone_input:20} | Valid: {is_valid} | Output: {result}")

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
