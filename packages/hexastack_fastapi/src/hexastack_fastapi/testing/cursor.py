"""Visual virtual cursor overlay script and human mouse emulation for feature demo recordings."""

from __future__ import annotations

import os
from typing import Any

from playwright.sync_api import Locator, Page

VIRTUAL_CURSOR_SCRIPT = """
(() => {
    let mouseX = 100;
    let mouseY = 100;
    let cursor = null;
    let isPressed = false;

    window.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        if (cursor) {
            cursor.style.left = mouseX + 'px';
            cursor.style.top = mouseY + 'px';
        }
    }, { passive: true });

    window.addEventListener('mousedown', () => {
        isPressed = true;
        if (cursor) {
            cursor.style.backgroundColor = 'rgba(16, 185, 129, 0.9)'; // emerald-500
            cursor.style.transform = 'translate(-50%, -50%) scale(1.4)';
        }
    }, { passive: true });

    window.addEventListener('mouseup', () => {
        isPressed = false;
        if (cursor) {
            cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.8)';
            cursor.style.transform = 'translate(-50%, -50%) scale(1.0)';
        }
    }, { passive: true });

    const initCursor = () => {
        if (document.getElementById('playwright-virtual-cursor')) return;

        cursor = document.createElement('div');
        cursor.id = 'playwright-virtual-cursor';
        cursor.style.position = 'fixed';
        cursor.style.left = mouseX + 'px';
        cursor.style.top = mouseY + 'px';
        cursor.style.width = '24px';
        cursor.style.height = '24px';
        cursor.style.borderRadius = '50%';
        cursor.style.backgroundColor = isPressed ? 'rgba(16, 185, 129, 0.9)' : 'rgba(239, 68, 68, 0.8)';
        cursor.style.border = '3px solid #fff';
        cursor.style.boxShadow = '0 0 10px rgba(0,0,0,0.5), 0 0 5px rgba(239, 68, 68, 0.8)';
        cursor.style.pointerEvents = 'none';
        cursor.style.zIndex = '2147483647';
        cursor.style.transition = 'transform 0.1s ease-out, background-color 0.1s ease';
        cursor.style.transform = isPressed ? 'translate(-50%, -50%) scale(1.4)' : 'translate(-50%, -50%) scale(1.0)';

        const root = document.documentElement || document.body;
        if (root) {
            root.appendChild(cursor);
        }
    };

    const interval = setInterval(() => {
        const parent = document.documentElement || document.body;
        if (parent) {
            initCursor();
            clearInterval(interval);
        }
    }, 50);

    window.addEventListener('DOMContentLoaded', initCursor);
})();
"""


def smart_click(page: Page, locator: Locator | Any, steps: int = 35) -> None:
    """Emulate human-like smooth mouse movement, pause, and click for demo recordings.

    If RECORD_DEMO is not active, executes instant locator.first.click() for maximum test speed.
    """
    record_mode = os.environ.get("RECORD_DEMO") in ("1", "true", "True")
    element = locator.first if hasattr(locator, "first") else locator

    if not record_mode:
        element.click()
        return

    element.scroll_into_view_if_needed()
    box = element.bounding_box()
    if not box:
        element.click()
        return

    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2

    # Smooth human mouse movement
    page.mouse.move(x, y, steps=steps)
    page.wait_for_timeout(800)  # Human-like pause showing target focus

    # Visual click ripple
    page.mouse.down()
    page.wait_for_timeout(300)
    page.mouse.up()
    page.wait_for_timeout(600)  # Settle delay


__all__ = [
    "smart_click",
    "VIRTUAL_CURSOR_SCRIPT",
]
