#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stylesheet generation for the Qt launcher."""

from gui_qt.theme import palette
from gui_qt.theme.assets import asset_path


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        color: {palette.TEXT_MAIN};
        font-family: "Microsoft YaHei UI", "Segoe UI";
        font-size: 13px;
    }}
    QWidget#appRoot {{
        background: transparent;
    }}
    QWidget#appShell {{
        background: {palette.WINDOW_BG};
        border: 1px solid {palette.BORDER};
        border-radius: 14px;
    }}
    QWidget#homePage, QWidget#settingsPage, QWidget#triggerPage, QWidget#logsPage {{
        background: {palette.WINDOW_BG};
    }}
    QLabel, QCheckBox {{
        background: transparent;
    }}
    QMainWindow {{
        background: {palette.WINDOW_BG};
    }}
    QWidget#titleBar {{
        background: #101114;
        border: 1px solid {palette.BORDER};
        border-radius: 8px;
    }}
    QLabel#titleIcon {{
        color: {palette.TEXT_MAIN};
        font-size: 15px;
        min-width: 22px;
    }}
    QLabel#titleCaption {{
        font-size: 12px;
        font-weight: 600;
        color: {palette.TEXT_MAIN};
    }}
    QPushButton#titleButton, QPushButton#titleCloseButton {{
        min-width: 30px;
        max-width: 30px;
        min-height: 24px;
        max-height: 24px;
        padding: 0;
        border-radius: 4px;
    }}
    QPushButton#titleCloseButton:hover {{
        background: #9b2323;
        border-color: #9b2323;
        color: #ffffff;
    }}
    QLabel#headerSubtitle, QLabel#statusBadge, QLabel#contentHint, QLabel#contentInfo {{
        color: {palette.TEXT_SUB};
    }}
    QTabWidget::pane {{
        border: 0;
        top: -1px;
    }}
    QTabWidget#mainTabs::tab-bar {{
        left: 18px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {palette.TEXT_MAIN};
        min-width: 118px;
        padding: 8px 8px 12px 8px;
        margin-right: 24px;
        border-bottom: 2px solid transparent;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        color: {palette.ACCENT};
        border-bottom: 2px solid {palette.ACCENT};
    }}
    QWidget#taskPanel, QWidget#contentPanel, QWidget#statusStrip, QWidget#contentFooter, QWidget#taskBottomPanel {{
        background: {palette.SURFACE_BG};
        border: 1px solid {palette.BORDER};
        border-radius: 8px;
    }}
    QWidget#taskListContainer, QWidget#taskRow {{
        background: transparent;
        border: 0;
    }}
    QWidget#taskRow:hover {{
        background: rgba(255, 255, 255, 0.03);
        border-radius: 4px;
    }}
    QWidget#taskRow[dragging="true"] {{
        background: rgba(4, 164, 255, 0.09);
        border: 1px solid rgba(4, 164, 255, 0.35);
        border-radius: 4px;
    }}
    QFrame#taskSeparator {{
        color: {palette.BORDER};
        background: {palette.BORDER};
        border: 0;
        max-height: 1px;
    }}
    QWidget#topStatusPanel {{
        background: transparent;
        border: 0;
    }}
    QWidget#statusGroup, QWidget#configGroup {{
        background: transparent;
        border: 0;
    }}
    QWidget#taskCard {{
        background: {palette.PANEL_ALT_BG};
        border: 1px solid {palette.BORDER};
        border-radius: 6px;
    }}
    QLabel#sectionTitle {{
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#taskMeta, QLabel#taskDescription {{
        color: {palette.TEXT_SUB};
        font-size: 12px;
    }}
    QPushButton {{
        background: {palette.BUTTON_BG};
        border: 1px solid {palette.BORDER};
        border-radius: 4px;
        min-height: 30px;
        padding: 4px 16px;
    }}
    QPushButton:hover {{
        background: {palette.BUTTON_HOVER};
    }}
    QPushButton#primaryButton {{
        border-color: {palette.ACCENT};
        color: {palette.ACCENT};
        font-weight: 700;
    }}
    QPushButton#miniButton {{
        min-width: 28px;
        max-width: 28px;
        padding: 0;
    }}
    QWidget#taskCard QPushButton {{
        min-height: 32px;
    }}
    QWidget#taskCard QPushButton#miniButton {{
        min-height: 32px;
        max-height: 32px;
    }}
    QPlainTextEdit#logView {{
        background: #0f1216;
        border: 1px solid {palette.BORDER};
        border-radius: 8px;
        color: #dce5ee;
        selection-background-color: {palette.ACCENT_DIM};
    }}
    QProgressBar#updateProgressBar {{
        min-width: 220px;
        max-width: 280px;
        min-height: 30px;
        border: 1px solid {palette.BORDER};
        border-radius: 6px;
        background: #11151a;
        color: {palette.TEXT_MAIN};
        text-align: center;
    }}
    QProgressBar#updateProgressBar::chunk {{
        border-radius: 5px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {palette.ACCENT_DIM}, stop:1 {palette.ACCENT});
    }}
    QWidget#statusStrip QLabel {{
        font-size: 11px;
    }}
    QWidget#statusStrip QLabel#statusBadge {{
        color: {palette.TEXT_MAIN};
    }}
    QLabel#statusGroupLabel, QLabel#statusDriverLabel, QLabel#statusConnectionLabel {{
        color: {palette.TEXT_SUB};
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#statusGroupValue {{
        color: {palette.TEXT_MAIN};
        font-size: 12px;
        font-weight: 600;
    }}
    QWidget#statusStrip {{
        border-radius: 6px;
    }}
    QWidget#topStatusPanel QWidget#statusStrip {{
        min-width: 390px;
    }}
    QCheckBox {{
        spacing: 10px;
        color: {palette.TEXT_MAIN};
    }}
    QPushButton#backendToggle {{
        min-height: 32px;
        min-width: 104px;
        padding: 4px 16px;
        padding-left: 0px;
        text-align: center;
        border: 1px solid {palette.BORDER};
        border-radius: 6px;
        background: {palette.BUTTON_BG};
        color: {palette.TEXT_SUB};
        font-weight: 600;
    }}
    QPushButton#backendToggle:hover {{
        border-color: #4b5563;
        background: {palette.BUTTON_HOVER};
        color: {palette.TEXT_MAIN};
    }}
    QPushButton#backendToggle:checked {{
        border-color: {palette.ACCENT};
        background: rgba(0, 167, 255, 0.14);
        color: {palette.TEXT_MAIN};
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        image: url("{asset_path("checkbox_unchecked.svg").replace("\\", "/")}");
    }}
    QCheckBox::indicator:checked {{
        image: url("{asset_path("checkbox_checked.svg").replace("\\", "/")}");
    }}
    """
