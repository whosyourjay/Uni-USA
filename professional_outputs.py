#!/usr/bin/env python3
"""Regenerate the compact law- and medical-school ability tables."""

import law
import medicine


def main():
    law.main()
    medicine.main()


if __name__ == "__main__":
    main()
