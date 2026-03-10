#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight motion primitives for a restrained desktop UI."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QEnterEvent, QMouseEvent, QPaintEvent, QPainter
from PySide6.QtWidgets import QGraphicsOpacityEffect, QPushButton, QTabWidget, QWidget


class AnimatedButton(QPushButton):
    """Push button with short hover and press transitions."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._hover_strength = 0.0
        self._press_strength = 0.0
        self.hover_animation = QPropertyAnimation(self, b"hoverStrength", self)
        self.hover_animation.setDuration(140)
        self.hover_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.press_animation = QPropertyAnimation(self, b"pressStrength", self)
        self.press_animation.setDuration(90)
        self.press_animation.setEasingCurve(QEasingCurve.OutQuad)

    def get_hover_strength(self) -> float:
        return self._hover_strength

    def set_hover_strength(self, value: float) -> None:
        self._hover_strength = max(0.0, min(1.0, float(value)))
        self.update()

    hoverStrength = Property(float, get_hover_strength, set_hover_strength)

    def get_press_strength(self) -> float:
        return self._press_strength

    def set_press_strength(self, value: float) -> None:
        self._press_strength = max(0.0, min(1.0, float(value)))
        self.update()

    pressStrength = Property(float, get_press_strength, set_press_strength)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._animate(self.hover_animation, self._hover_strength, 1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate(self.hover_animation, self._hover_strength, 0.0)
        self._animate(self.press_animation, self._press_strength, 0.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._animate(self.press_animation, self._press_strength, 1.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._animate(self.press_animation, self._press_strength, 0.0)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        overlay_alpha = int(22 * self._hover_strength)
        press_alpha = int(18 * self._press_strength)
        if overlay_alpha <= 0 and press_alpha <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        hover_color = QColor("#ffffff")
        hover_color.setAlpha(max(0, overlay_alpha - press_alpha))
        press_color = QColor("#00a7ff")
        press_color.setAlpha(press_alpha)
        if hover_color.alpha() > 0:
            painter.fillRect(rect, hover_color)
        if press_color.alpha() > 0:
            painter.fillRect(rect, press_color)

    def _animate(self, animation: QPropertyAnimation, start: float, end: float) -> None:
        animation.stop()
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.start()


class AnimatedTabWidget(QTabWidget):
    """Tab widget with a short fade-in on page changes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.page_fade_effect = QGraphicsOpacityEffect(self)
        self.page_fade_animation = QPropertyAnimation(self.page_fade_effect, b"opacity", self)
        self.page_fade_animation.setDuration(180)
        self.page_fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.currentChanged.connect(self._animate_current_page)

    def _animate_current_page(self, index: int) -> None:
        page = self.widget(index)
        if page is None:
            return
        page.setGraphicsEffect(self.page_fade_effect)
        self.page_fade_animation.stop()
        self.page_fade_animation.setStartValue(0.82)
        self.page_fade_animation.setEndValue(1.0)
        self.page_fade_animation.start()


class BackendToggleButton(AnimatedButton):
    """Checkable backend selector button."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
