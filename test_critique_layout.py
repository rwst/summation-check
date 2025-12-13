#!/usr/bin/env python3
"""
Test script for CritiqueWindow layout with lorem ipsum content.
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui_view import CritiqueWindow
from prep_ai_critique import CritiqueResult

LOREM_SHORT = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."

LOREM_MEDIUM = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."""

LOREM_LONG = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.

Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt."""


def main():
    app = QApplication(sys.argv)

    # Create a mock CritiqueResult with lorem ipsum text
    mock_result = CritiqueResult(
        Critique=LOREM_LONG,
        SummaryOfCritique=LOREM_MEDIUM,
        ImprovedShortText=LOREM_SHORT
    )

    # Create and show the CritiqueWindow
    window = CritiqueWindow(mock_result)
    window.exec_()

    sys.exit(0)


if __name__ == '__main__':
    main()
