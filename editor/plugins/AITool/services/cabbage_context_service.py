"""World-scoped persistence, guidance tasks, and adaptive assistance scoring."""

from __future__ import annotations

import configparser
import json
import logging
import os
import socket
import shutil
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from utils.settings import settings_manager

from .node_graph_review_service import NodeGraphReviewService

logger = logging.getLogger(__name__)


class CabbageContextService:
    SCHEMA_VERSION = 2
    CONTEXT_DIR = "CabbageAssistant"
    CONTEXT_FILE = "context.json"
    MAX_RECENT_EVENTS = 200
    MAX_PROFILE_HISTORY = 50
    MAX_ISSUE_MEMORY = 200
    MAX_SCORE_TASKS = 24
    MAX_GOAL_PLAN_TASKS = 24
    GOAL_VISIBLE_TASKS = 2
    GOAL_PLAN_TIMEOUT_SECONDS = 45
    SCORE_MIN_INTERVAL_SECONDS = 300
    GOAL_COMPLETION_SIGNALS = {
        "model_imported",
        "object_transformed",
        "lighting_adjusted",
        "physics_adjusted",
        "node_created",
        "node_moved",
        "nodes_connected",
        "block_added",
        "block_parameter_changed",
        "transition_condition_set",
        "node_graph_run",
        "run_succeeded",
    }
    GOAL_NODE_SIGNALS = {
        "node_created",
        "node_moved",
        "nodes_connected",
        "block_added",
        "block_parameter_changed",
        "transition_condition_set",
        "node_graph_run",
        "run_succeeded",
    }
    GOAL_SCENE_SIGNALS = {
        "model_imported",
        "object_transformed",
        "lighting_adjusted",
        "physics_adjusted",
    }
    GOAL_PHASES = {"node-logic", "scene-polish"}
    MIN_GOAL_NODE_TASKS = 5
    ISSUE_PATTERN_FIELDS = (
        "blockType", "workspaceRole", "relationType",
        "missingInput", "objectRequirement", "edgeId",
    )
    CHAT_GUIDANCE_INTENTS = {
        "connect_object_reference", "select_existing_object", "create_node",
        "move_node", "connect_nodes", "drag_block", "edit_block_parameter",
        "set_transition_condition", "run_node_graph", "import_model",
        "transform_model", "adjust_lighting", "adjust_physics",
    }
    IMPORTANT_EVENT_TYPES = {
        "model_imported",
        "actor_created",
        "actor_deleted",
        "transform_position",
        "transform_rotation",
        "transform_scale",
        "lighting_changed",
        "physics_changed",
        "node_edited",
        "node_created",
        "node_moved",
        "node_connected",
        "block_added",
        "block_parameter_changed",
        "node_issue_found",
        "node_issue_fixed",
        "run_started",
        "run_succeeded",
        "run_failed",
        "tutorial_completed",
        "goal_task_completed",
    }
    METRIC_BY_EVENT = {
        "model_imported": "modelImports",
        "transform_position": "transformEdits",
        "transform_rotation": "transformEdits",
        "transform_scale": "transformEdits",
        "lighting_changed": "lightingEdits",
        "physics_changed": "physicsEdits",
        "node_edited": "nodeEdits",
        "node_created": "nodeEdits",
        "node_moved": "nodeEdits",
        "node_connected": "nodeEdits",
        "block_added": "nodeEdits",
        "block_parameter_changed": "nodeEdits",
        "node_issue_found": "nodeErrors",
        "node_issue_fixed": "nodeIssueFixes",
        "run_succeeded": "runSuccesses",
        "run_failed": "runFailures",
    }
    TUTORIAL_CHAPTERS = tuple([
        {
                "chapterKey": "chapter_viewport",
                "chapterOrder": 1,
                "chapterTitle": "\u7b2c\u4e00\u7ae0\uff1a\u7b2c\u4e00\u6b21\u770b\u89c1\u4e16\u754c",
                "chapterTitleEn": "Chapter 1: See the World for the First Time",
                "chapterSummary": "\u805a\u7126\u4e3b\u89c6\u53e3\uff0c\u7528\u952e\u76d8\u548c\u9f20\u6807\u5b66\u4f1a\u79fb\u52a8\u3001\u65cb\u8f6c\u6444\u50cf\u673a\u3002",
                "chapterSummaryEn": "Focus the viewport and learn to move the camera with the keyboard and mouse."
        },
        {
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely."
        },
        {
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks."
        },
        {
                "chapterKey": "chapter_preview",
                "chapterOrder": 4,
                "chapterTitle": "\u7ec8\u7ae0\uff1a\u8fd0\u884c\u4f60\u7684\u4e16\u754c",
                "chapterTitleEn": "Final Chapter: Run Your World",
                "chapterSummary": "\u542f\u52a8\u5e76\u7ed3\u675f\u9879\u76ee\u9884\u89c8\uff0c\u786e\u8ba4\u4e16\u754c\u80fd\u5b8c\u6574\u6062\u590d\u3002",
                "chapterSummaryEn": "Start and stop project preview, confirming that the world restores cleanly."
        }
])
    TUTORIAL_TASKS = tuple([
        {
                "taskKey": "tutorial.basics.viewport_focus",
                "type": "tutorial",
                "chapterKey": "chapter_viewport",
                "chapterOrder": 1,
                "chapterTitle": "\u7b2c\u4e00\u7ae0\uff1a\u7b2c\u4e00\u6b21\u770b\u89c1\u4e16\u754c",
                "chapterTitleEn": "Chapter 1: See the World for the First Time",
                "chapterSummary": "\u805a\u7126\u4e3b\u89c6\u53e3\uff0c\u7528\u952e\u76d8\u548c\u9f20\u6807\u5b66\u4f1a\u79fb\u52a8\u3001\u65cb\u8f6c\u6444\u50cf\u673a\u3002",
                "chapterSummaryEn": "Focus the viewport and learn to move the camera with the keyboard and mouse.",
                "chapterTaskOrder": 1,
                "globalOrder": 1,
                "order": 1,
                "title": "\u805a\u7126 3D \u4e3b\u89c6\u53e3",
                "titleEn": "Focus the 3D Viewport",
                "message": "\u70b9\u51fb\u4e00\u6b21 3D \u4e3b\u89c6\u53e3\uff0c\u8ba9\u5b83\u63a5\u6536\u952e\u76d8\u548c\u9f20\u6807\u8f93\u5165\u3002",
                "messageEn": "Click the 3D viewport once so it receives keyboard and mouse input.",
                "suggestion": "\u70b9\u51fb\u4e2d\u592e\u663e\u793a\u573a\u666f\u7684\u533a\u57df\u3002",
                "suggestionEn": "Click the central area where the scene is displayed.",
                "completionCriteria": "\u4e3b\u89c6\u53e3\u83b7\u5f97\u8f93\u5165\u7126\u70b9\u3002",
                "completionCriteriaEn": "The main viewport receives input focus.",
                "guidanceIntent": "focus_viewport"
        },
        {
                "taskKey": "tutorial.basics.camera_forward_back",
                "type": "tutorial",
                "chapterKey": "chapter_viewport",
                "chapterOrder": 1,
                "chapterTitle": "\u7b2c\u4e00\u7ae0\uff1a\u7b2c\u4e00\u6b21\u770b\u89c1\u4e16\u754c",
                "chapterTitleEn": "Chapter 1: See the World for the First Time",
                "chapterSummary": "\u805a\u7126\u4e3b\u89c6\u53e3\uff0c\u7528\u952e\u76d8\u548c\u9f20\u6807\u5b66\u4f1a\u79fb\u52a8\u3001\u65cb\u8f6c\u6444\u50cf\u673a\u3002",
                "chapterSummaryEn": "Focus the viewport and learn to move the camera with the keyboard and mouse.",
                "chapterTaskOrder": 2,
                "globalOrder": 2,
                "order": 2,
                "title": "\u524d\u540e\u79fb\u52a8\u6444\u50cf\u673a",
                "titleEn": "Move the Camera Forward or Backward",
                "message": "\u6309 W \u6216 S\uff0c\u8ba9\u6444\u50cf\u673a\u5b9e\u9645\u5411\u524d\u6216\u5411\u540e\u79fb\u52a8\u3002",
                "messageEn": "Press W or S and make the camera actually move forward or backward.",
                "suggestion": "\u6309\u4f4f W \u6216 S \u7247\u523b\uff0c\u76f4\u5230\u753b\u9762\u4f4d\u7f6e\u53d1\u751f\u53d8\u5316\u3002",
                "suggestionEn": "Hold W or S briefly until the view position changes.",
                "completionCriteria": "\u68c0\u6d4b\u5230 W/S \u5bfc\u81f4\u6444\u50cf\u673a\u5b9e\u9645\u4f4d\u79fb\u3002",
                "completionCriteriaEn": "W or S causes a measurable camera translation.",
                "guidanceIntent": "move_camera_forward_back"
        },
        {
                "taskKey": "tutorial.basics.camera_left_right",
                "type": "tutorial",
                "chapterKey": "chapter_viewport",
                "chapterOrder": 1,
                "chapterTitle": "\u7b2c\u4e00\u7ae0\uff1a\u7b2c\u4e00\u6b21\u770b\u89c1\u4e16\u754c",
                "chapterTitleEn": "Chapter 1: See the World for the First Time",
                "chapterSummary": "\u805a\u7126\u4e3b\u89c6\u53e3\uff0c\u7528\u952e\u76d8\u548c\u9f20\u6807\u5b66\u4f1a\u79fb\u52a8\u3001\u65cb\u8f6c\u6444\u50cf\u673a\u3002",
                "chapterSummaryEn": "Focus the viewport and learn to move the camera with the keyboard and mouse.",
                "chapterTaskOrder": 3,
                "globalOrder": 3,
                "order": 3,
                "title": "\u5de6\u53f3\u79fb\u52a8\u6444\u50cf\u673a",
                "titleEn": "Move the Camera Left or Right",
                "message": "\u6309 A \u6216 D\uff0c\u8ba9\u6444\u50cf\u673a\u5b9e\u9645\u5411\u5de6\u6216\u5411\u53f3\u79fb\u52a8\u3002",
                "messageEn": "Press A or D and make the camera actually move left or right.",
                "suggestion": "\u6309\u4f4f A \u6216 D \u7247\u523b\uff0c\u89c2\u5bdf\u753b\u9762\u6a2a\u5411\u53d8\u5316\u3002",
                "suggestionEn": "Hold A or D briefly and watch the view shift sideways.",
                "completionCriteria": "\u68c0\u6d4b\u5230 A/D \u5bfc\u81f4\u6444\u50cf\u673a\u5b9e\u9645\u4f4d\u79fb\u3002",
                "completionCriteriaEn": "A or D causes a measurable camera translation.",
                "guidanceIntent": "move_camera_left_right"
        },
        {
                "taskKey": "tutorial.basics.camera_up_down",
                "type": "tutorial",
                "chapterKey": "chapter_viewport",
                "chapterOrder": 1,
                "chapterTitle": "\u7b2c\u4e00\u7ae0\uff1a\u7b2c\u4e00\u6b21\u770b\u89c1\u4e16\u754c",
                "chapterTitleEn": "Chapter 1: See the World for the First Time",
                "chapterSummary": "\u805a\u7126\u4e3b\u89c6\u53e3\uff0c\u7528\u952e\u76d8\u548c\u9f20\u6807\u5b66\u4f1a\u79fb\u52a8\u3001\u65cb\u8f6c\u6444\u50cf\u673a\u3002",
                "chapterSummaryEn": "Focus the viewport and learn to move the camera with the keyboard and mouse.",
                "chapterTaskOrder": 4,
                "globalOrder": 4,
                "order": 4,
                "title": "\u4e0a\u4e0b\u79fb\u52a8\u6444\u50cf\u673a",
                "titleEn": "Move the Camera Up or Down",
                "message": "\u6309 Q \u6216 E\uff0c\u8ba9\u6444\u50cf\u673a\u5b9e\u9645\u5411\u4e0b\u6216\u5411\u4e0a\u79fb\u52a8\u3002",
                "messageEn": "Press Q or E and make the camera actually move down or up.",
                "suggestion": "\u6309\u4f4f Q \u6216 E \u7247\u523b\uff0c\u89c2\u5bdf\u9ad8\u5ea6\u53d8\u5316\u3002",
                "suggestionEn": "Hold Q or E briefly and watch the camera height change.",
                "completionCriteria": "\u68c0\u6d4b\u5230 Q/E \u5bfc\u81f4\u6444\u50cf\u673a\u5b9e\u9645\u4f4d\u79fb\u3002",
                "completionCriteriaEn": "Q or E causes a measurable camera translation.",
                "guidanceIntent": "move_camera_up_down"
        },
        {
                "taskKey": "tutorial.basics.camera_rotate",
                "type": "tutorial",
                "chapterKey": "chapter_viewport",
                "chapterOrder": 1,
                "chapterTitle": "\u7b2c\u4e00\u7ae0\uff1a\u7b2c\u4e00\u6b21\u770b\u89c1\u4e16\u754c",
                "chapterTitleEn": "Chapter 1: See the World for the First Time",
                "chapterSummary": "\u805a\u7126\u4e3b\u89c6\u53e3\uff0c\u7528\u952e\u76d8\u548c\u9f20\u6807\u5b66\u4f1a\u79fb\u52a8\u3001\u65cb\u8f6c\u6444\u50cf\u673a\u3002",
                "chapterSummaryEn": "Focus the viewport and learn to move the camera with the keyboard and mouse.",
                "chapterTaskOrder": 5,
                "globalOrder": 5,
                "order": 5,
                "title": "\u8f6c\u52a8\u6444\u50cf\u673a\u89c6\u89d2",
                "titleEn": "Rotate the Camera View",
                "message": "\u5728\u89c6\u53e3\u4e2d\u6309\u4f4f\u9f20\u6807\u53f3\u952e\u5e76\u62d6\u52a8\uff0c\u5b9e\u9645\u8f6c\u52a8\u6444\u50cf\u673a\u89c6\u89d2\u3002",
                "messageEn": "Hold the right mouse button in the viewport and drag to actually rotate the camera.",
                "suggestion": "\u5728\u4e3b\u89c6\u53e3\u5185\u53f3\u952e\u6309\u4f4f\u540e\u6c34\u5e73\u6216\u5782\u76f4\u62d6\u52a8\u3002",
                "suggestionEn": "Hold the right mouse button inside the main viewport and drag horizontally or vertically.",
                "completionCriteria": "\u68c0\u6d4b\u5230\u53f3\u952e\u62d6\u52a8\u5bfc\u81f4\u6444\u50cf\u673a\u671d\u5411\u53d8\u5316\u3002",
                "completionCriteriaEn": "A right-mouse drag causes a measurable camera rotation.",
                "guidanceIntent": "rotate_camera"
        },
        {
                "taskKey": "tutorial.basics.camera_wheel",
                "type": "tutorial",
                "chapterKey": "chapter_viewport",
                "chapterOrder": 1,
                "chapterTitle": "\u7b2c\u4e00\u7ae0\uff1a\u7b2c\u4e00\u6b21\u770b\u89c1\u4e16\u754c",
                "chapterTitleEn": "Chapter 1: See the World for the First Time",
                "chapterSummary": "\u805a\u7126\u4e3b\u89c6\u53e3\uff0c\u7528\u952e\u76d8\u548c\u9f20\u6807\u5b66\u4f1a\u79fb\u52a8\u3001\u65cb\u8f6c\u6444\u50cf\u673a\u3002",
                "chapterSummaryEn": "Focus the viewport and learn to move the camera with the keyboard and mouse.",
                "chapterTaskOrder": 6,
                "globalOrder": 6,
                "order": 6,
                "title": "\u7528\u6eda\u8f6e\u79fb\u52a8\u6444\u50cf\u673a",
                "titleEn": "Move the Camera with the Wheel",
                "message": "\u6eda\u52a8\u9f20\u6807\u6eda\u8f6e\uff0c\u8ba9\u6444\u50cf\u673a\u5b9e\u9645\u524d\u8fdb\u6216\u540e\u9000\u3002",
                "messageEn": "Scroll the mouse wheel and make the camera actually move forward or backward.",
                "suggestion": "\u5c06\u9f20\u6807\u653e\u5728\u4e3b\u89c6\u53e3\u4e0a\uff0c\u5411\u4e0a\u6216\u5411\u4e0b\u6eda\u52a8\u3002",
                "suggestionEn": "Place the pointer over the main viewport and scroll up or down.",
                "completionCriteria": "\u6eda\u8f6e\u5bfc\u81f4\u6444\u50cf\u673a\u4ea7\u751f\u5b9e\u9645\u4f4d\u79fb\u3002",
                "completionCriteriaEn": "The wheel causes a measurable camera translation.",
                "guidanceIntent": "move_camera_wheel"
        },
        {
                "taskKey": "tutorial.basics.open_scene_manager",
                "type": "tutorial",
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely.",
                "chapterTaskOrder": 1,
                "globalOrder": 7,
                "order": 7,
                "title": "\u6253\u5f00\u573a\u666f\u7ba1\u7406",
                "titleEn": "Open Scene Manager",
                "message": "\u70b9\u51fb\u201c\u573a\u666f\u7ba1\u7406\u201d\u5feb\u6377\u6309\u94ae\uff0c\u6253\u5f00\u573a\u666f\u7ba1\u7406\u7a97\u53e3\u3002",
                "messageEn": "Click the Scene Manager shortcut to open the Scene Manager window.",
                "suggestion": "\u8bf7\u4eb2\u81ea\u70b9\u51fb\u5feb\u6377\u6309\u94ae\uff1b\u64cd\u4f5c\u5c55\u793a\u81ea\u52a8\u6253\u5f00\u4e0d\u4f1a\u5b8c\u6210\u4efb\u52a1\u3002",
                "suggestionEn": "Click the shortcut yourself; a panel opened automatically by guidance does not complete this task.",
                "completionCriteria": "\u7528\u6237\u6765\u6e90\u7684 SceneTools panel_opened \u4e8b\u4ef6\u3002",
                "completionCriteriaEn": "A user-sourced SceneTools panel_opened event is received.",
                "guidanceIntent": "open_scene_manager"
        },
        {
                "taskKey": "tutorial.basics.import_model",
                "type": "tutorial",
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely.",
                "chapterTaskOrder": 2,
                "globalOrder": 8,
                "order": 8,
                "title": "\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b",
                "titleEn": "Import a Model",
                "message": "\u901a\u8fc7\u573a\u666f\u7ba1\u7406\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\uff0c\u5e76\u5c06\u5b83\u7ed1\u5b9a\u4e3a\u6559\u7a0b\u6a21\u578b\u3002",
                "messageEn": "Import a model through Scene Manager and bind it as the tutorial model.",
                "suggestion": "\u5728\u573a\u666f\u7ba1\u7406\u4e2d\u9009\u62e9\u4e00\u4e2a\u6a21\u578b\u8d44\u6e90\u5e76\u5bfc\u5165\u5f53\u524d\u573a\u666f\u3002",
                "suggestionEn": "Choose a model asset in Scene Manager and import it into the current scene.",
                "completionCriteria": "\u6a21\u578b\u5bfc\u5165\u6210\u529f\uff0c\u5e76\u8bb0\u5f55\u5176\u573a\u666f\u548c\u5bf9\u8c61 ID\u3002",
                "completionCriteriaEn": "The model imports successfully and its scene and actor IDs are recorded.",
                "guidanceIntent": "import_model"
        },
        {
                "taskKey": "tutorial.basics.select_model",
                "type": "tutorial",
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely.",
                "chapterTaskOrder": 3,
                "globalOrder": 9,
                "order": 9,
                "title": "\u9009\u4e2d\u6559\u7a0b\u6a21\u578b",
                "titleEn": "Select the Tutorial Model",
                "message": "\u5728\u573a\u666f\u6811\u6216\u89c6\u53e3\u4e2d\u4e3b\u52a8\u9009\u4e2d\u521a\u5bfc\u5165\u7684\u6a21\u578b\u3002",
                "messageEn": "Actively select the model you just imported in the scene tree or viewport.",
                "suggestion": "\u70b9\u51fb\u573a\u666f\u6811\u4e2d\u521a\u521a\u5bfc\u5165\u7684\u6a21\u578b\u540d\u79f0\u3002",
                "suggestionEn": "Click the newly imported model name in the scene tree.",
                "completionCriteria": "\u7528\u6237\u9009\u4e2d\u7684\u5bf9\u8c61\u4e0e\u6559\u7a0b\u7ed1\u5b9a\u6a21\u578b\u4e00\u81f4\u3002",
                "completionCriteriaEn": "The user-selected actor matches the bound tutorial model.",
                "guidanceIntent": "select_model"
        },
        {
                "taskKey": "tutorial.basics.set_position_x",
                "type": "tutorial",
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely.",
                "chapterTaskOrder": 4,
                "globalOrder": 10,
                "order": 10,
                "title": "\u5c06\u4f4d\u7f6e X \u8bbe\u4e3a 1",
                "titleEn": "Set Position X to 1",
                "message": "\u5c06\u6559\u7a0b\u6a21\u578b\u7684\u4f4d\u7f6e X \u8bbe\u7f6e\u4e3a 1\u3002",
                "messageEn": "Set the tutorial model's Position X to 1.",
                "suggestion": "\u5728\u5bf9\u8c61\u5c5e\u6027\u7684\u53d8\u6362\u533a\u57df\uff0c\u628a\u4f4d\u7f6e X \u8f93\u5165\u4e3a 1\u3002",
                "suggestionEn": "In the Transform section of Object Properties, enter 1 for Position X.",
                "completionCriteria": "\u7ed1\u5b9a\u6a21\u578b\u7684\u4f4d\u7f6e X \u4e3a 1\uff0c\u5bb9\u5dee \u00b10.01\u3002",
                "completionCriteriaEn": "The bound model's Position X is 1 within \u00b10.01.",
                "guidanceIntent": "set_position_x"
        },
        {
                "taskKey": "tutorial.basics.set_rotation_y",
                "type": "tutorial",
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely.",
                "chapterTaskOrder": 5,
                "globalOrder": 11,
                "order": 11,
                "title": "\u5c06\u65cb\u8f6c Y \u8bbe\u4e3a 45",
                "titleEn": "Set Rotation Y to 45",
                "message": "\u5c06\u6559\u7a0b\u6a21\u578b\u7684\u65cb\u8f6c Y \u8bbe\u7f6e\u4e3a 45 \u5ea6\u3002",
                "messageEn": "Set the tutorial model's Rotation Y to 45 degrees.",
                "suggestion": "\u5728\u53d8\u6362\u533a\u57df\uff0c\u628a\u65cb\u8f6c Y \u8f93\u5165\u4e3a 45\u3002",
                "suggestionEn": "In the Transform section, enter 45 for Rotation Y.",
                "completionCriteria": "\u7ed1\u5b9a\u6a21\u578b\u7684\u65cb\u8f6c Y \u4e3a 45\u00b0\uff0c\u5bb9\u5dee \u00b10.1\u00b0\u3002",
                "completionCriteriaEn": "The bound model's Rotation Y is 45\u00b0 within \u00b10.1\u00b0.",
                "guidanceIntent": "set_rotation_y"
        },
        {
                "taskKey": "tutorial.basics.set_scale_x",
                "type": "tutorial",
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely.",
                "chapterTaskOrder": 6,
                "globalOrder": 12,
                "order": 12,
                "title": "\u5c06\u7f29\u653e X \u8bbe\u4e3a 1.5",
                "titleEn": "Set Scale X to 1.5",
                "message": "\u5c06\u6559\u7a0b\u6a21\u578b\u7684\u7f29\u653e X \u8bbe\u7f6e\u4e3a 1.5\u3002",
                "messageEn": "Set the tutorial model's Scale X to 1.5.",
                "suggestion": "\u5728\u53d8\u6362\u533a\u57df\uff0c\u628a\u7f29\u653e X \u8f93\u5165\u4e3a 1.5\u3002",
                "suggestionEn": "In the Transform section, enter 1.5 for Scale X.",
                "completionCriteria": "\u7ed1\u5b9a\u6a21\u578b\u7684\u7f29\u653e X \u4e3a 1.5\uff0c\u5bb9\u5dee \u00b10.01\u3002",
                "completionCriteriaEn": "The bound model's Scale X is 1.5 within \u00b10.01.",
                "guidanceIntent": "set_scale_x"
        },
        {
                "taskKey": "tutorial.basics.enable_physics",
                "type": "tutorial",
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely.",
                "chapterTaskOrder": 7,
                "globalOrder": 13,
                "order": 13,
                "title": "\u5f00\u542f\u7269\u7406\u6a21\u62df",
                "titleEn": "Enable Physics Simulation",
                "message": "\u786e\u4fdd\u6559\u7a0b\u6a21\u578b\u7684\u201c\u7269\u7406\u6a21\u62df\u201d\u5904\u4e8e\u542f\u7528\u72b6\u6001\u3002",
                "messageEn": "Make sure Physics Simulation is enabled for the tutorial model.",
                "suggestion": "\u5728\u5bf9\u8c61\u7269\u7406\u5c5e\u6027\u4e2d\u6253\u5f00\u201c\u7269\u7406\u6a21\u62df\u201d\u5f00\u5173\u3002",
                "suggestionEn": "Turn on the Physics Simulation switch in the object's physics properties.",
                "completionCriteria": "\u7ed1\u5b9a\u6a21\u578b\u6536\u5230 SetPhysicsEnabled=true\u3002",
                "completionCriteriaEn": "The bound model receives SetPhysicsEnabled=true.",
                "guidanceIntent": "enable_physics"
        },
        {
                "taskKey": "tutorial.basics.set_mass",
                "type": "tutorial",
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely.",
                "chapterTaskOrder": 8,
                "globalOrder": 14,
                "order": 14,
                "title": "\u5c06\u8d28\u91cf\u8bbe\u4e3a 10",
                "titleEn": "Set Mass to 10",
                "message": "\u5c06\u6559\u7a0b\u6a21\u578b\u7684\u8d28\u91cf\u8bbe\u7f6e\u4e3a 10\u3002",
                "messageEn": "Set the tutorial model's mass to 10.",
                "suggestion": "\u5728\u7269\u7406\u5c5e\u6027\u4e2d\u627e\u5230\u8d28\u91cf\uff0c\u8f93\u5165 10\u3002",
                "suggestionEn": "Find Mass in the physics properties and enter 10.",
                "completionCriteria": "\u7ed1\u5b9a\u6a21\u578b\u7684\u8d28\u91cf\u4e3a 10\uff0c\u5bb9\u5dee \u00b10.01\u3002",
                "completionCriteriaEn": "The bound model's mass is 10 within \u00b10.01.",
                "guidanceIntent": "set_mass"
        },
        {
                "taskKey": "tutorial.basics.set_light_x",
                "type": "tutorial",
                "chapterKey": "chapter_scene",
                "chapterOrder": 2,
                "chapterTitle": "\u7b2c\u4e8c\u7ae0\uff1a\u628a\u7269\u4f53\u653e\u8fdb\u4e16\u754c",
                "chapterTitleEn": "Chapter 2: Put an Object into the World",
                "chapterSummary": "\u6253\u5f00\u573a\u666f\u7ba1\u7406\uff0c\u5bfc\u5165\u4e00\u4e2a\u6a21\u578b\u5e76\u7cbe\u786e\u8c03\u6574\u5b83\u7684\u5c5e\u6027\u3002",
                "chapterSummaryEn": "Open Scene Manager, import a tutorial model, and adjust it precisely.",
                "chapterTaskOrder": 9,
                "globalOrder": 15,
                "order": 15,
                "title": "\u5c06\u5149\u7167\u65b9\u5411 X \u8bbe\u4e3a 0.5",
                "titleEn": "Set Light Direction X to 0.5",
                "message": "\u5c06\u573a\u666f\u5149\u7167\u65b9\u5411 X \u8bbe\u7f6e\u4e3a 0.5\u3002",
                "messageEn": "Set Scene Light Direction X to 0.5.",
                "suggestion": "\u5728\u573a\u666f\u7ba1\u7406\u7684\u5149\u7167\u8bbe\u7f6e\u4e2d\uff0c\u628a\u65b9\u5411 X \u8f93\u5165\u4e3a 0.5\u3002",
                "suggestionEn": "In Scene Manager's lighting settings, enter 0.5 for Direction X.",
                "completionCriteria": "\u5f53\u524d\u573a\u666f\u5149\u7167\u65b9\u5411 X \u4e3a 0.5\uff0c\u5bb9\u5dee \u00b10.01\u3002",
                "completionCriteriaEn": "The current scene's Light Direction X is 0.5 within \u00b10.01.",
                "guidanceIntent": "set_light_x"
        },
        {
                "taskKey": "tutorial.basics.open_nodes",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 1,
                "globalOrder": 16,
                "order": 16,
                "title": "\u6253\u5f00\u8282\u70b9\u7a97\u53e3",
                "titleEn": "Open the Nodes Window",
                "message": "\u70b9\u51fb\u201c\u8282\u70b9\u201d\u5feb\u6377\u6309\u94ae\uff0c\u6253\u5f00\u8282\u70b9\u7a97\u53e3\u3002",
                "messageEn": "Click the Nodes shortcut to open the Nodes window.",
                "suggestion": "\u8bf7\u4eb2\u81ea\u70b9\u51fb\u8282\u70b9\u5feb\u6377\u6309\u94ae\u3002",
                "suggestionEn": "Click the Nodes shortcut yourself.",
                "completionCriteria": "\u7528\u6237\u6765\u6e90\u7684 NodeGraphPanel panel_opened \u4e8b\u4ef6\u3002",
                "completionCriteriaEn": "A user-sourced NodeGraphPanel panel_opened event is received.",
                "guidanceIntent": "open_nodes"
        },
        {
                "taskKey": "tutorial.basics.confirm_start_node",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 2,
                "globalOrder": 17,
                "order": 17,
                "title": "\u521b\u5efa\u6216\u786e\u8ba4\u5f00\u59cb\u8282\u70b9",
                "titleEn": "Create or Confirm a Start Node",
                "message": "\u521b\u5efa\u6216\u786e\u8ba4\u4e00\u4e2a\u201c\u5f00\u59cb\u8282\u70b9\u201d\uff1b\u5df2\u6709\u552f\u4e00\u5f00\u59cb\u8282\u70b9\u65f6\u53ef\u76f4\u63a5\u70b9\u51fb\u786e\u8ba4\u3002",
                "messageEn": "Create or confirm a Start node; if one unique Start node already exists, click it to confirm.",
                "suggestion": "\u82e5\u753b\u5e03\u4e0a\u5df2\u6709\u5f00\u59cb\u8282\u70b9\uff0c\u70b9\u51fb\u5b83\uff1b\u5426\u5219\u62d6\u5165\u7b2c\u4e00\u4e2a\u8282\u70b9\u3002",
                "suggestionEn": "If a Start node already exists, click it; otherwise drag the first node onto the canvas.",
                "completionCriteria": "\u7ed1\u5b9a\u552f\u4e00\u7684\u5f00\u59cb\u8282\u70b9 ID\u3002",
                "completionCriteriaEn": "The unique Start node ID is bound.",
                "guidanceIntent": "confirm_start_node"
        },
        {
                "taskKey": "tutorial.basics.create_custom_node",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 3,
                "globalOrder": 18,
                "order": 18,
                "title": "\u521b\u5efa\u81ea\u5b9a\u4e49\u8282\u70b9",
                "titleEn": "Create a Custom Node",
                "message": "\u518d\u62d6\u5165\u4e00\u4e2a\u8282\u70b9\uff0c\u5e76\u786e\u8ba4\u5176\u7c7b\u578b\u4e3a\u201c\u81ea\u5b9a\u4e49\u8282\u70b9\u201d\u3002",
                "messageEn": "Drag in another node and confirm that its type is Custom Node.",
                "suggestion": "\u4ece\u5de5\u5177\u533a\u518d\u62d6\u4e00\u4e2a\u8282\u70b9\u5230\u753b\u5e03\u3002",
                "suggestionEn": "Drag one more node from the toolbox onto the canvas.",
                "completionCriteria": "\u65b0\u5efa\u8282\u70b9\u7c7b\u578b\u4e3a custom\uff0c\u5e76\u7ed1\u5b9a\u5176 ID\u3002",
                "completionCriteriaEn": "A new node of type custom is created and its ID is bound.",
                "guidanceIntent": "create_custom_node"
        },
        {
                "taskKey": "tutorial.basics.move_custom_node",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 4,
                "globalOrder": 19,
                "order": 19,
                "title": "\u79fb\u52a8\u81ea\u5b9a\u4e49\u8282\u70b9",
                "titleEn": "Move the Custom Node",
                "message": "\u6309\u4f4f\u521a\u521b\u5efa\u7684\u81ea\u5b9a\u4e49\u8282\u70b9\uff0c\u5c06\u5b83\u62d6\u5230\u65b0\u7684\u4f4d\u7f6e\u3002",
                "messageEn": "Hold the Custom node you just created and drag it to a new position.",
                "suggestion": "\u62d6\u52a8\u8282\u70b9\u6807\u9898\u533a\uff0c\u8ba9\u5b83\u79bb\u5f00\u539f\u4f4d\u7f6e\u3002",
                "suggestionEn": "Drag the node header so it leaves its original position.",
                "completionCriteria": "\u7ed1\u5b9a\u7684\u81ea\u5b9a\u4e49\u8282\u70b9\u4ea7\u751f\u5b9e\u9645\u4f4d\u79fb\u3002",
                "completionCriteriaEn": "The bound Custom node has a measurable position change.",
                "guidanceIntent": "move_custom_node"
        },
        {
                "taskKey": "tutorial.basics.connect_nodes",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 5,
                "globalOrder": 20,
                "order": 20,
                "title": "\u8fde\u63a5\u4e24\u4e2a\u8282\u70b9",
                "titleEn": "Connect the Two Nodes",
                "message": "\u5c06\u5f00\u59cb\u8282\u70b9\u8fde\u63a5\u5230\u81ea\u5b9a\u4e49\u8282\u70b9\u3002",
                "messageEn": "Connect the Start node to the Custom node.",
                "suggestion": "\u4ece\u5f00\u59cb\u8282\u70b9\u7684\u8f93\u51fa\u7aef\u53e3\u62d6\u5230\u81ea\u5b9a\u4e49\u8282\u70b9\u7684\u8f93\u5165\u7aef\u53e3\u3002",
                "suggestionEn": "Drag from the Start node's output port to the Custom node's input port.",
                "completionCriteria": "\u8fde\u7ebf\u6e90\u548c\u76ee\u6807\u5206\u522b\u5339\u914d\u7ed1\u5b9a\u7684\u5f00\u59cb\u4e0e\u81ea\u5b9a\u4e49\u8282\u70b9\u3002",
                "completionCriteriaEn": "The connection source and target match the bound Start and Custom nodes.",
                "guidanceIntent": "connect_nodes"
        },
        {
                "taskKey": "tutorial.basics.open_custom_node",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 6,
                "globalOrder": 21,
                "order": 21,
                "title": "\u6253\u5f00\u81ea\u5b9a\u4e49\u8282\u70b9",
                "titleEn": "Open the Custom Node",
                "message": "\u70b9\u51fb\u81ea\u5b9a\u4e49\u8282\u70b9\uff0c\u6253\u5f00\u5b83\u7684\u5185\u90e8\u79ef\u6728\u7f16\u8f91\u533a\u3002",
                "messageEn": "Click the Custom node to open its internal block editor.",
                "suggestion": "\u5355\u51fb\u521a\u8fde\u63a5\u7684\u81ea\u5b9a\u4e49\u8282\u70b9\u3002",
                "suggestionEn": "Click the Custom node you just connected.",
                "completionCriteria": "\u9009\u4e2d\u7684\u8282\u70b9 ID \u4e0e\u7ed1\u5b9a\u7684\u81ea\u5b9a\u4e49\u8282\u70b9\u4e00\u81f4\u3002",
                "completionCriteriaEn": "The selected node ID matches the bound Custom node.",
                "guidanceIntent": "open_custom_node"
        },
        {
                "taskKey": "tutorial.basics.add_when_enter",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 7,
                "globalOrder": 22,
                "order": 22,
                "title": "\u6dfb\u52a0\u8fdb\u5165\u8282\u70b9\u4e8b\u4ef6",
                "titleEn": "Add the Node Enter Event",
                "message": "\u5c06\u201c\u5f53\u8fdb\u5165\u5f53\u524d\u8282\u70b9\u65f6\u201d\u79ef\u6728 node_when_enter \u62d6\u5165\u8be5\u8282\u70b9\u3002",
                "messageEn": "Drag the node_when_enter block into this node.",
                "suggestion": "\u5728\u79ef\u6728\u5de5\u5177\u7bb1\u4e2d\u627e\u5230\u4e8b\u4ef6\u79ef\u6728\u5e76\u62d6\u5165\u3002",
                "suggestionEn": "Find the event block in the block toolbox and drag it in.",
                "completionCriteria": "\u7ed1\u5b9a\u81ea\u5b9a\u4e49\u8282\u70b9\u4e2d\u65b0\u589e node_when_enter\u3002",
                "completionCriteriaEn": "node_when_enter is added to the bound Custom node.",
                "guidanceIntent": "add_when_enter"
        },
        {
                "taskKey": "tutorial.basics.add_wait",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 8,
                "globalOrder": 23,
                "order": 23,
                "title": "\u8fde\u63a5\u7b49\u5f85\u79ef\u6728",
                "titleEn": "Connect a Wait Block",
                "message": "\u5c06\u201c\u7b49\u5f85\u201d\u79ef\u6728 control_wait \u62d6\u5165\uff0c\u5e76\u8fde\u63a5\u5230\u8fdb\u5165\u4e8b\u4ef6\u4e0b\u65b9\u3002",
                "messageEn": "Drag in control_wait and connect it below the enter event.",
                "suggestion": "\u62d6\u5165\u201c\u7b49\u5f85\u201d\u79ef\u6728\uff0c\u5c06\u9876\u90e8\u8fde\u63a5\u53e3\u5438\u9644\u5230 node_when_enter \u7684\u8bed\u53e5\u533a\u3002",
                "suggestionEn": "Drag in Wait and snap its connector into the statement area of node_when_enter.",
                "completionCriteria": "control_wait \u5df2\u8fde\u63a5\uff0c\u4e14\u7236\u79ef\u6728\u4e3a node_when_enter\u3002",
                "completionCriteriaEn": "control_wait is connected with node_when_enter as its parent.",
                "guidanceIntent": "add_wait"
        },
        {
                "taskKey": "tutorial.basics.set_wait_seconds",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 9,
                "globalOrder": 24,
                "order": 24,
                "title": "\u5c06\u7b49\u5f85\u65f6\u95f4\u8bbe\u4e3a 2 \u79d2",
                "titleEn": "Set Wait Time to 2 Seconds",
                "message": "\u5c06\u7b49\u5f85\u79ef\u6728\u7684 SECONDS \u53c2\u6570\u4fee\u6539\u4e3a 2\u3002",
                "messageEn": "Change the Wait block's SECONDS parameter to 2.",
                "suggestion": "\u70b9\u51fb\u201c\u7b49\u5f85\u201d\u79ef\u6728\u4e2d\u7684\u6570\u5b57\u8f93\u5165\u6846\uff0c\u8f93\u5165 2\u3002",
                "suggestionEn": "Click the number field in Wait and enter 2.",
                "completionCriteria": "\u7ed1\u5b9a control_wait \u7684 SECONDS \u4e3a 2\uff0c\u5bb9\u5dee \u00b10.01\u3002",
                "completionCriteriaEn": "The bound control_wait has SECONDS=2 within \u00b10.01.",
                "guidanceIntent": "set_wait_seconds"
        },
        {
                "taskKey": "tutorial.basics.select_edge",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 10,
                "globalOrder": 25,
                "order": 25,
                "title": "\u6253\u5f00\u8fde\u7ebf\u6761\u4ef6\u533a",
                "titleEn": "Open the Connection Condition Area",
                "message": "\u70b9\u51fb\u5f00\u59cb\u8282\u70b9\u4e0e\u81ea\u5b9a\u4e49\u8282\u70b9\u4e4b\u95f4\u7684\u8fde\u7ebf\u3002",
                "messageEn": "Click the connection between the Start and Custom nodes.",
                "suggestion": "\u70b9\u51fb\u4e24\u4e2a\u8282\u70b9\u4e4b\u95f4\u7684\u7ebf\u6216\u6761\u4ef6\u6807\u7b7e\u3002",
                "suggestionEn": "Click the line or condition label between the two nodes.",
                "completionCriteria": "\u9009\u4e2d\u7684\u8fde\u7ebf ID \u4e0e\u6559\u7a0b\u7ed1\u5b9a\u8fde\u7ebf\u4e00\u81f4\u3002",
                "completionCriteriaEn": "The selected edge ID matches the bound tutorial connection.",
                "guidanceIntent": "select_edge"
        },
        {
                "taskKey": "tutorial.basics.add_true_condition",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 11,
                "globalOrder": 26,
                "order": 26,
                "title": "\u6dfb\u52a0\u771f\u503c\u6761\u4ef6",
                "titleEn": "Add a TRUE Condition",
                "message": "\u5728\u6761\u4ef6\u7f16\u8f91\u533a\u62d6\u5165 logic_boolean\uff0c\u5e76\u786e\u4fdd\u503c\u4e3a\u201c\u771f/TRUE\u201d\u3002",
                "messageEn": "Drag logic_boolean into the condition area and make sure it is TRUE.",
                "suggestion": "\u4ece\u201c\u503c\u201d\u5206\u7c7b\u62d6\u5165\u5e03\u5c14\u503c\u79ef\u6728\uff0c\u5e76\u5c06\u4e0b\u62c9\u503c\u8bbe\u4e3a\u771f\u3002",
                "suggestionEn": "Drag a Boolean value block from Values and set it to TRUE.",
                "completionCriteria": "\u7ed1\u5b9a\u8fde\u7ebf\u7684\u6761\u4ef6\u533a\u6709\u4e00\u4e2a\u9876\u5c42 TRUE \u5e03\u5c14\u79ef\u6728\u3002",
                "completionCriteriaEn": "The bound connection condition has one top-level Boolean set to TRUE.",
                "guidanceIntent": "add_true_condition"
        },
        {
                "taskKey": "tutorial.basics.run_graph",
                "type": "tutorial",
                "chapterKey": "chapter_nodes",
                "chapterOrder": 3,
                "chapterTitle": "\u7b2c\u4e09\u7ae0\uff1a\u8ba9\u4e16\u754c\u52a8\u8d77\u6765",
                "chapterTitleEn": "Chapter 3: Bring the World to Life",
                "chapterSummary": "\u4f7f\u7528\u8282\u70b9\u3001\u8fde\u7ebf\u548c\u79ef\u6728\u642d\u5efa\u5e76\u8fd0\u884c\u7b2c\u4e00\u6bb5\u53ef\u89c6\u5316\u903b\u8f91\u3002",
                "chapterSummaryEn": "Build and run your first visual logic with nodes, connections, and blocks.",
                "chapterTaskOrder": 12,
                "globalOrder": 27,
                "order": 27,
                "title": "\u8fd0\u884c\u8282\u70b9\u56fe",
                "titleEn": "Run the Node Graph",
                "message": "\u70b9\u51fb\u201c\u8fd0\u884c\u201d\uff0c\u7b49\u5f85\u8282\u70b9\u56fe\u771f\u6b63\u8fd4\u56de\u6210\u529f\u3002",
                "messageEn": "Click Run and wait for the node graph to report success.",
                "suggestion": "\u70b9\u51fb\u8282\u70b9\u7a97\u53e3\u53f3\u4e0a\u89d2\u7684\u201c\u8fd0\u884c\u201d\u3002",
                "suggestionEn": "Click Run in the upper-right corner of the Nodes window.",
                "completionCriteria": "\u6536\u5230 run_succeeded\u3002",
                "completionCriteriaEn": "run_succeeded is received.",
                "guidanceIntent": "run_node_graph"
        },
        {
                "taskKey": "tutorial.basics.start_preview",
                "type": "tutorial",
                "chapterKey": "chapter_preview",
                "chapterOrder": 4,
                "chapterTitle": "\u7ec8\u7ae0\uff1a\u8fd0\u884c\u4f60\u7684\u4e16\u754c",
                "chapterTitleEn": "Final Chapter: Run Your World",
                "chapterSummary": "\u542f\u52a8\u5e76\u7ed3\u675f\u9879\u76ee\u9884\u89c8\uff0c\u786e\u8ba4\u4e16\u754c\u80fd\u5b8c\u6574\u6062\u590d\u3002",
                "chapterSummaryEn": "Start and stop project preview, confirming that the world restores cleanly.",
                "chapterTaskOrder": 1,
                "globalOrder": 28,
                "order": 28,
                "title": "\u5f00\u59cb\u9879\u76ee\u9884\u89c8",
                "titleEn": "Start Project Preview",
                "message": "\u70b9\u51fb\u201c\u5f00\u59cb\u9884\u89c8\u201d\uff0c\u7b49\u5f85\u9879\u76ee\u771f\u6b63\u8fdb\u5165 running \u72b6\u6001\u3002",
                "messageEn": "Click Start Preview and wait for the project to enter the running state.",
                "suggestion": "\u70b9\u51fb\u4e3b\u89c6\u53e3\u4e0a\u65b9\u7684\u201c\u5f00\u59cb\u9884\u89c8\u201d\u3002",
                "suggestionEn": "Click Start Preview above the main viewport.",
                "completionCriteria": "\u9879\u76ee\u9884\u89c8\u72b6\u6001\u53d8\u4e3a running\u3002",
                "completionCriteriaEn": "Project preview reaches running.",
                "guidanceIntent": "start_preview"
        },
        {
                "taskKey": "tutorial.basics.stop_preview",
                "type": "tutorial",
                "chapterKey": "chapter_preview",
                "chapterOrder": 4,
                "chapterTitle": "\u7ec8\u7ae0\uff1a\u8fd0\u884c\u4f60\u7684\u4e16\u754c",
                "chapterTitleEn": "Final Chapter: Run Your World",
                "chapterSummary": "\u542f\u52a8\u5e76\u7ed3\u675f\u9879\u76ee\u9884\u89c8\uff0c\u786e\u8ba4\u4e16\u754c\u80fd\u5b8c\u6574\u6062\u590d\u3002",
                "chapterSummaryEn": "Start and stop project preview, confirming that the world restores cleanly.",
                "chapterTaskOrder": 2,
                "globalOrder": 29,
                "order": 29,
                "title": "\u7ed3\u675f\u9879\u76ee\u9884\u89c8",
                "titleEn": "Stop Project Preview",
                "message": "\u70b9\u51fb\u201c\u7ed3\u675f\u9884\u89c8\u201d\uff0c\u7b49\u5f85\u9884\u89c8\u5b8c\u5168\u505c\u6b62\u5e76\u6210\u529f\u6062\u590d\u573a\u666f\u3002",
                "messageEn": "Click Stop Preview and wait until preview stops and the scene is restored.",
                "suggestion": "\u70b9\u51fb\u201c\u7ed3\u675f\u9884\u89c8\u201d\uff0c\u4fdd\u6301\u7f16\u8f91\u5668\u6253\u5f00\u3002",
                "suggestionEn": "Click Stop Preview and keep the editor open.",
                "completionCriteria": "\u9884\u89c8\u5b8c\u5168\u505c\u6b62\uff0c\u573a\u666f\u6062\u590d\u6210\u529f\u4e14\u65e0\u9519\u8bef\u3002",
                "completionCriteriaEn": "Preview fully stops and its scene restoration succeeds.",
                "guidanceIntent": "stop_preview"
        }
])
    RETIRED_TUTORIAL_TASK_KEYS = {'tutorial.import_model', 'tutorial.transform_model', 'tutorial.adjust_lighting', 'tutorial.adjust_physics', 'tutorial.create_node', 'tutorial.move_node', 'tutorial.connect_nodes', 'tutorial.drag_block', 'tutorial.edit_block_parameter', 'tutorial.set_transition_condition', 'tutorial.run_node_graph', 'tutorial.rotate_model'}
    TUTORIAL_TOTAL_TASKS = 29
    TUTORIAL_VALUE_TOLERANCE = 0.01
    TUTORIAL_ROTATION_TOLERANCE = 0.1
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="CabbageAssistant")
        self._score_tasks: dict[str, dict[str, Any]] = {}
        self._goal_plan_tasks: dict[str, dict[str, Any]] = {}
        self._closed = False

    @staticmethod
    def _error(code: str, message: str) -> dict[str, Any]:
        return {"success": False, "status": "error", "error": code, "message": message}

    @staticmethod
    def _clone(value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False))

    @classmethod
    def _merge_baseline(cls, current: Any, incoming: Any) -> dict[str, Any]:
        """Merge later baseline sections without overwriting the first captured value."""
        result = cls._clone(current) if isinstance(current, dict) else {}
        if not isinstance(incoming, dict):
            return result
        for key, value in incoming.items():
            if key not in result:
                result[key] = cls._clone(value)
            elif isinstance(result.get(key), dict) and isinstance(value, dict):
                result[key] = cls._merge_baseline(result[key], value)
        return result

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @classmethod
    def _active_project_path(cls) -> Path:
        # settings_manager is the authoritative world resolver. Its property already
        # hydrates from last_project when no world has been activated yet; forcing
        # last_project on every request can overwrite a newer in-memory world switch.
        project_path = settings_manager.active_project_path
        if not project_path:
            raise RuntimeError("当前没有打开世界")
        path = Path(project_path).expanduser().resolve()
        if not (path / "project.ini").is_file():
            raise RuntimeError("当前世界目录无效")
        return path

    @classmethod
    def _context_path(cls, project_path: Path) -> Path:
        return project_path / cls.CONTEXT_DIR / cls.CONTEXT_FILE

    @staticmethod
    def _project_goal_metadata(project_path: Path) -> tuple[str, str]:
        project_file = project_path / "project.ini"
        if not project_file.is_file():
            return "", "story"
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(project_file, encoding="utf-8-sig")
            section = parser["Project"] if parser.has_section("Project") else parser.defaults()
            prompt = str(section.get("world_prompt") or section.get("prompt") or "").strip()[:4000]
            mode = str(section.get("mode") or "story").strip().lower()
        except Exception:
            logger.debug("Unable to read world prompt from project.ini: %s", project_file, exc_info=True)
            return "", "story"
        if mode not in {"story", "creative"}:
            mode = "story"
        return prompt, mode

    @staticmethod
    def _needs_project_goal_plan(context: dict[str, Any], prompt: str, mode: str) -> bool:
        if not prompt:
            return False
        goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
        same_goal = (
            str(goal.get("prompt") or "").strip() == prompt
            and str(goal.get("mode") or "story").strip().lower() == mode
            and goal.get("source") == "ai"
        )
        if not same_goal:
            return True
        has_goal_plan = any(
            isinstance(task, dict) and task.get("type") == "goal"
            for task in [*(context.get("activeTasks") or []), *(context.get("taskHistory") or [])]
        )
        return goal.get("status") == "ready" and not has_goal_plan

    @staticmethod
    def _validate_payload_world(project_path: Path, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        expected = str(payload.get("worldId") or "").strip()
        if expected and expected != project_path.name:
            raise ValueError("请求属于其他世界，已忽略迟到的上下文写入")

    @classmethod
    def _tutorial_templates(cls) -> dict[str, dict[str, Any]]:
        return {str(task["taskKey"]): task for task in cls.TUTORIAL_TASKS}

    @staticmethod
    def _custom_goal_enabled(context: dict[str, Any]) -> bool:
        goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
        if (not str(goal.get("prompt") or "").strip()
                or goal.get("source") != "ai"
                or goal.get("status") != "ready"):
            return False
        return any(
            isinstance(task, dict) and task.get("type") == "goal"
            for task in [*(context.get("activeTasks") or []), *(context.get("taskHistory") or [])]
        )

    @classmethod
    def _ensure_goal_slots_locked(cls, context: dict[str, Any], now: int) -> None:
        history_keys = {
            str(task.get("taskKey") or "")
            for task in context.get("taskHistory") or []
            if isinstance(task, dict) and task.get("type") == "goal"
        }
        normalized: list[dict[str, Any]] = []
        for raw in context.get("activeTasks") or []:
            if not isinstance(raw, dict):
                continue
            if raw.get("type") != "goal":
                normalized.append(raw)
                continue
            task_key = str(raw.get("taskKey") or "")
            if not task_key or task_key in history_keys:
                continue
            task = dict(raw)
            task["status"] = str(task.get("status") or "queued")
            normalized.append(task)
        context["activeTasks"] = normalized

        goal_tasks = sorted(
            (task for task in normalized if task.get("type") == "goal"),
            key=lambda task: int(task.get("order") or 0),
        )
        visible = [task for task in goal_tasks if task.get("status") in {"active", "pending"}]
        selected_keys = {str(task.get("taskKey") or "") for task in visible[: cls.GOAL_VISIBLE_TASKS]}
        if len(selected_keys) < cls.GOAL_VISIBLE_TASKS:
            for task in goal_tasks:
                key = str(task.get("taskKey") or "")
                if key in selected_keys:
                    continue
                selected_keys.add(key)
                if len(selected_keys) >= cls.GOAL_VISIBLE_TASKS:
                    break
        for task in goal_tasks:
            next_status = "active" if str(task.get("taskKey") or "") in selected_keys else "queued"
            if task.get("status") != next_status:
                task["status"] = next_status
                task["updatedAt"] = now

    @classmethod
    def _ensure_task_slots_locked(cls, context: dict[str, Any], now: int) -> None:
        if cls._custom_goal_enabled(context):
            context["activeTasks"] = [
                task for task in context.get("activeTasks") or []
                if not isinstance(task, dict) or task.get("type") != "tutorial"
            ]
            cls._ensure_goal_slots_locked(context, now)
            return
        context["activeTasks"] = [
            task for task in context.get("activeTasks") or []
            if not isinstance(task, dict) or task.get("type") != "goal"
        ]
        cls._ensure_tutorial_slots_locked(context, now)

    @classmethod
    def _ensure_tutorial_slots_locked(cls, context: dict[str, Any], now: int) -> None:
        """Keep exactly one basic tutorial task active and all later steps queued."""
        templates = cls._tutorial_templates()
        history_keys = {
            str(task.get("taskKey") or "")
            for task in context.get("taskHistory") or []
            if isinstance(task, dict) and task.get("type") == "tutorial"
        }
        session = context.get("tutorialSession") if isinstance(context.get("tutorialSession"), dict) else {}
        session_status = str(session.get("status") or "active")
        tutorial_finished = session_status in {"restoring", "completed", "restore_failed"}

        normalized_tasks: list[dict[str, Any]] = []
        for raw in context.get("activeTasks") or []:
            if not isinstance(raw, dict):
                continue
            task_key = str(raw.get("taskKey") or "")
            template = templates.get(task_key)
            if task_key in cls.RETIRED_TUTORIAL_TASK_KEYS:
                continue
            if raw.get("type") != "tutorial":
                normalized_tasks.append(raw)
                continue
            if not template or task_key in history_keys or tutorial_finished:
                continue
            task = dict(raw)
            task.update(template)
            task.pop("track", None)
            task.pop("discipline", None)
            normalized_tasks.append(task)
        context["activeTasks"] = normalized_tasks

        if tutorial_finished:
            return

        existing_keys = {
            str(task.get("taskKey") or "")
            for task in context["activeTasks"]
            if isinstance(task, dict)
        }
        for template in cls.TUTORIAL_TASKS:
            task_key = str(template["taskKey"])
            if task_key in history_keys or task_key in existing_keys:
                continue
            task = dict(template)
            task.update({
                "status": "queued",
                "createdAt": now,
                "updatedAt": now,
                "completedAt": 0,
                "resolvedAt": 0,
            })
            context["activeTasks"].append(task)

        tutorial_tasks = sorted(
            (
                task for task in context["activeTasks"]
                if isinstance(task, dict) and task.get("type") == "tutorial"
            ),
            key=lambda task: int(task.get("globalOrder") or task.get("order") or 0),
        )
        selected = tutorial_tasks[0] if tutorial_tasks else None
        for task in tutorial_tasks:
            next_status = "active" if task is selected else "queued"
            if task.get("status") != next_status:
                task["status"] = next_status
                task["updatedAt"] = now

    @classmethod
    def _default_tutorial_session(cls, now: int) -> dict[str, Any]:
        return {
            "sessionId": f"tutorial_{uuid.uuid4().hex}",
            "status": "active",
            "startedAt": now,
            "restoredAt": 0,
            "bindings": {
                "sceneName": "",
                "modelActorName": "",
                "modelActorId": "",
                "modelResourcePath": "",
                "startNodeId": "",
                "startNodeCreatedByTutorial": False,
                "customNodeId": "",
                "edgeId": "",
                "whenEnterBlockId": "",
                "waitBlockId": "",
                "conditionBlockId": "",
            },
            "baseline": {},
            "modificationLog": [],
            "lastRestoreError": "",
            "completionNoticeExpiresAt": 0,
        }

    @classmethod
    def _normalize_tutorial_session(cls, raw: Any, now: int) -> dict[str, Any]:
        default = cls._default_tutorial_session(now)
        if not isinstance(raw, dict):
            return default
        session = dict(default)
        session["sessionId"] = str(raw.get("sessionId") or default["sessionId"])[:180]
        status = str(raw.get("status") or "active")
        session["status"] = status if status in {"active", "restoring", "completed", "restore_failed"} else "active"
        for key in ("startedAt", "restoredAt", "completionNoticeExpiresAt"):
            session[key] = max(0, int(raw.get(key) or 0))
        if not session["startedAt"]:
            session["startedAt"] = now
        session["lastRestoreError"] = str(raw.get("lastRestoreError") or "")[:2000]
        raw_bindings = raw.get("bindings") if isinstance(raw.get("bindings"), dict) else {}
        bindings = dict(default["bindings"])
        for key in bindings:
            if key == "startNodeCreatedByTutorial":
                bindings[key] = bool(raw_bindings.get(key))
            else:
                bindings[key] = str(raw_bindings.get(key) or "")[:500]
        session["bindings"] = bindings
        session["baseline"] = cls._clone(raw.get("baseline")) if isinstance(raw.get("baseline"), dict) else {}
        raw_log = raw.get("modificationLog") if isinstance(raw.get("modificationLog"), list) else []
        session["modificationLog"] = [cls._clone(item) for item in raw_log if isinstance(item, dict)][-200:]
        return session

    @classmethod
    def _default_context(cls, project_path: Path) -> dict[str, Any]:
        now = cls._now_ms()
        context = {
            "schemaVersion": cls.SCHEMA_VERSION,
            "worldId": project_path.name,
            "projectPathIdentity": os.path.normcase(str(project_path)),
            "profile": {
                "score": 0,
                "source": "deepseek",
                "updatedAt": 0,
                "reasonCodes": [],
                "lastScoredEventCount": 0,
            },
            "profileHistory": [],
            "issueMemory": {},
            "metrics": {
                "modelImports": 0,
                "transformEdits": 0,
                "lightingEdits": 0,
                "physicsEdits": 0,
                "nodeEdits": 0,
                "nodeErrors": 0,
                "nodeIssueFixes": 0,
                "runSuccesses": 0,
                "runFailures": 0,
                "importantEventCount": 0,
                "firstActivityAt": 0,
                "lastActivityAt": 0,
            },
            "tutorialProgress": {
                "positionChanged": False,
                "scaleChanged": False,
            },
            "tutorialSession": cls._default_tutorial_session(now),
            "worldGoal": {
                "prompt": "",
                "mode": "story",
                "source": "default",
                "status": "ready",
                "generatedAt": 0,
                "generationError": "",
                "generationId": "",
            },
            "goalTaskPlan": {
                "schemaVersion": 2,
                "generatedAt": 0,
                "taskCount": 0,
                "nodeTaskCount": 0,
                "sceneTaskCount": 0,
                "logicBlueprint": {},
            },
            "goalSignalCounts": {},
            "activeTasks": [],
            "taskHistory": [],
            "chatMessages": [],
            "recentOperationEvents": [],
            "updatedAt": now,
        }
        cls._ensure_task_slots_locked(context, now)
        return context

    @classmethod
    def _normalize_context(cls, value: Any, project_path: Path) -> dict[str, Any]:
        default = cls._default_context(project_path)
        if not isinstance(value, dict):
            return default
        value["schemaVersion"] = cls.SCHEMA_VERSION
        value["worldId"] = project_path.name
        value["projectPathIdentity"] = os.path.normcase(str(project_path))
        raw_profile = value.get("profile") if isinstance(value.get("profile"), dict) else {}
        legacy_score = raw_profile.get("score", raw_profile.get("fluencyScore", 0))
        try:
            normalized_score = max(0, min(int(round(float(legacy_score or 0))), 100))
        except (TypeError, ValueError):
            normalized_score = 0
        value["profile"] = {
            "score": normalized_score,
            "source": str(raw_profile.get("source") or "deepseek")[:40],
            "updatedAt": max(0, int(raw_profile.get("updatedAt") or 0)),
            "reasonCodes": [
                str(item)[:80]
                for item in (raw_profile.get("reasonCodes") or raw_profile.get("fluencyReasonCodes") or [])
                if str(item).strip()
            ][:12],
            "lastScoredEventCount": max(0, int(raw_profile.get("lastScoredEventCount", raw_profile.get("lastClassifiedEventCount", 0)) or 0)),
        }
        for key in ("metrics", "tutorialProgress", "worldGoal", "goalTaskPlan"):
            merged = dict(default[key])
            if isinstance(value.get(key), dict):
                merged.update(value[key])
            value[key] = merged
        value["tutorialSession"] = cls._normalize_tutorial_session(value.get("tutorialSession"), cls._now_ms())
        if not isinstance(value.get("goalSignalCounts"), dict):
            value["goalSignalCounts"] = {}
        value["goalSignalCounts"] = {
            str(key)[:80]: max(0, int(count or 0))
            for key, count in value["goalSignalCounts"].items()
            if str(key) in cls.GOAL_COMPLETION_SIGNALS
        }
        for key in ("profileHistory", "activeTasks", "taskHistory", "chatMessages", "recentOperationEvents"):
            if not isinstance(value.get(key), list):
                value[key] = []
        if not isinstance(value.get("issueMemory"), dict):
            value["issueMemory"] = {}
        now = cls._now_ms()
        cls._ensure_task_slots_locked(value, now)
        value["profileHistory"] = value["profileHistory"][-cls.MAX_PROFILE_HISTORY :]
        value["recentOperationEvents"] = value["recentOperationEvents"][-cls.MAX_RECENT_EVENTS :]
        cls._normalize_issue_memory_locked(value)
        value["updatedAt"] = int(value.get("updatedAt") or now)
        return value

    def _read_locked(self, project_path: Path) -> dict[str, Any]:
        path = self._context_path(project_path)
        if not path.is_file():
            context = self._default_context(project_path)
            self._write_locked(project_path, context)
            return context
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            context = self._normalize_context(value, project_path)
            return context
        except Exception:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            corrupt = path.with_name(f"context.{stamp}.corrupt.json")
            try:
                shutil.copy2(path, corrupt)
            except Exception:
                logger.debug("Failed to back up corrupt Cabbage context", exc_info=True)
            logger.warning("Cabbage context was invalid and has been reset: %s", path)
            context = self._default_context(project_path)
            self._write_locked(project_path, context)
            return context


    @classmethod
    def _normalize_issue_pattern(cls, raw: Any) -> dict[str, str]:
        if not isinstance(raw, dict):
            return {}
        normalized: dict[str, str] = {}
        for field in cls.ISSUE_PATTERN_FIELDS:
            value = str(raw.get(field) or "").strip()[:180]
            if value:
                normalized[field] = value
        return normalized

    @classmethod
    def _normalize_issue_memory_locked(cls, context: dict[str, Any]) -> None:
        raw_memory = context.get("issueMemory")
        normalized: dict[str, dict[str, Any]] = {}
        if isinstance(raw_memory, dict):
            for raw_code, raw_entry in raw_memory.items():
                code = str(raw_code or "").strip()[:180]
                if not code or not isinstance(raw_entry, dict):
                    continue
                normalized[code] = {
                    "occurrences": max(0, int(raw_entry.get("occurrences") or 0)),
                    "resolvedCount": max(0, int(raw_entry.get("resolvedCount") or 0)),
                    "chatDiscussionCount": max(0, int(raw_entry.get("chatDiscussionCount") or 0)),
                    "firstSeenAt": max(0, int(raw_entry.get("firstSeenAt") or 0)),
                    "lastSeenAt": max(0, int(raw_entry.get("lastSeenAt") or 0)),
                    "lastDiscussedAt": max(0, int(raw_entry.get("lastDiscussedAt") or 0)),
                    "pattern": cls._normalize_issue_pattern(raw_entry.get("pattern")),
                }

        if not normalized:
            for task in (context.get("activeTasks") or []) + (context.get("taskHistory") or []):
                if not isinstance(task, dict) or task.get("type") != "node-issue":
                    continue
                code = str(task.get("code") or task.get("issueKey") or task.get("taskKey") or "").strip()[:180]
                if not code:
                    continue
                entry = normalized.setdefault(code, {
                    "occurrences": 0, "resolvedCount": 0, "chatDiscussionCount": 0,
                    "firstSeenAt": 0, "lastSeenAt": 0, "lastDiscussedAt": 0, "pattern": {},
                })
                entry["occurrences"] += 1
                entry["pattern"].update(cls._normalize_issue_pattern(task.get("pattern")))
                seen_at = int(task.get("firstDetectedAt") or task.get("createdAt") or 0)
                entry["firstSeenAt"] = min(filter(None, (entry["firstSeenAt"], seen_at)), default=0)
                entry["lastSeenAt"] = max(entry["lastSeenAt"], seen_at)
                if task.get("status") == "resolved" or int(task.get("resolvedAt") or 0) > 0:
                    entry["resolvedCount"] += 1
            for message in context.get("chatMessages") or []:
                if not isinstance(message, dict) or message.get("role") != "user":
                    continue
                code = str(message.get("issueCode") or "").strip()[:180]
                if not code:
                    continue
                entry = normalized.setdefault(code, {
                    "occurrences": 0, "resolvedCount": 0, "chatDiscussionCount": 0,
                    "firstSeenAt": 0, "lastSeenAt": 0, "lastDiscussedAt": 0, "pattern": {},
                })
                entry["chatDiscussionCount"] += 1
                entry["lastDiscussedAt"] = max(entry["lastDiscussedAt"], int(message.get("createdAt") or 0))

        ordered = sorted(normalized.items(), key=lambda item: max(item[1]["lastSeenAt"], item[1]["lastDiscussedAt"]), reverse=True)
        context["issueMemory"] = dict(ordered[: cls.MAX_ISSUE_MEMORY])

    @classmethod
    def _issue_memory_entry_locked(cls, context: dict[str, Any], code: str) -> dict[str, Any]:
        cls._normalize_issue_memory_locked(context)
        key = str(code or "logic_issue").strip()[:180] or "logic_issue"
        return context["issueMemory"].setdefault(key, {
            "occurrences": 0,
            "resolvedCount": 0,
            "chatDiscussionCount": 0,
            "firstSeenAt": 0,
            "lastSeenAt": 0,
            "lastDiscussedAt": 0,
            "pattern": {},
        })

    def _write_locked(self, project_path: Path, context: dict[str, Any]) -> None:
        path = self._context_path(project_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        context["updatedAt"] = self._now_ms()
        temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temp_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, path)

    def load(self, payload: Any = None) -> dict[str, Any]:
        try:
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            project_prompt, project_mode = self._project_goal_metadata(project_path)
            with self._lock:
                context = self._read_locked(project_path)
                should_start_goal_plan = self._needs_project_goal_plan(
                    context, project_prompt, project_mode,
                )
                self._write_locked(project_path, context)

            goal_plan = None
            if should_start_goal_plan:
                # The creation page can disappear immediately after opening the world.
                # Recover from its missed/raced request by treating project.ini as the
                # durable source of the original world description.
                goal_plan = self.start_goal_plan({
                    "worldId": project_path.name,
                    "prompt": project_prompt,
                    "mode": project_mode,
                })
                with self._lock:
                    context = self._read_locked(project_path)

            response = {"success": True, "status": "ok", "context": self._clone(context)}
            if goal_plan is not None:
                response["goalPlan"] = self._clone(goal_plan)
            return response
        except Exception as exc:
            logger.warning("Unable to load Cabbage context: %s", exc)
            return self._error("CONTEXT_LOAD_FAILED", str(exc))

    @classmethod
    def _normalize_event(cls, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("\u5305\u83dc\u64cd\u4f5c\u4e8b\u4ef6\u683c\u5f0f\u4e0d\u6b63\u786e")
        event_type = str(payload.get("type") or "").strip()[:80]
        if not event_type:
            raise ValueError("\u5305\u83dc\u64cd\u4f5c\u4e8b\u4ef6\u7f3a\u5c11 type")
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        safe_details: dict[str, Any] = {}
        for key, raw in details.items():
            name = str(key)[:80]
            if isinstance(raw, (str, int, float, bool)) or raw is None:
                limit = 50000 if name in {"baselineJson", "modificationJson"} else 2000 if name in {"error", "restoreError"} else 500
                safe_details[name] = raw if not isinstance(raw, str) else raw[:limit]
        return {
            "eventId": str(payload.get("eventId") or f"event_{uuid.uuid4().hex}"),
            "type": event_type,
            "category": str(payload.get("category") or "editor")[:80],
            "success": payload.get("success") is not False,
            "timestamp": int(payload.get("timestamp") or cls._now_ms()),
            "details": safe_details,
        }

    @staticmethod
    def _find_task(context: dict[str, Any], task_key: str) -> dict[str, Any] | None:
        return next((task for task in context["activeTasks"] if isinstance(task, dict) and task.get("taskKey") == task_key), None)

    @classmethod
    def _complete_task_locked(cls, context: dict[str, Any], task_key: str, now: int) -> bool:
        task = cls._find_task(context, task_key)
        if not task:
            return False
        context["activeTasks"].remove(task)
        task = dict(task)
        task.update({"status": "completed", "updatedAt": now, "completedAt": now})
        context["taskHistory"].append(task)
        return True

    @staticmethod
    def _detail_text(details: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = str(details.get(key) or "").strip()
            if value:
                return value
        return ""

    @staticmethod
    def _detail_number(details: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            raw = details.get(key)
            try:
                if raw is not None and str(raw).strip() != "":
                    return float(raw)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _detail_bool(details: dict[str, Any], *keys: str) -> bool | None:
        for key in keys:
            raw = details.get(key)
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, (int, float)):
                return bool(raw)
            text = str(raw or "").strip().lower()
            if text in {"true", "1", "yes", "on", "enabled", "running", "stopped"}:
                return True
            if text in {"false", "0", "no", "off", "disabled", ""}:
                return False
        return None

    @classmethod
    def _active_tutorial_task(cls, context: dict[str, Any]) -> dict[str, Any] | None:
        tasks = [
            task for task in context.get("activeTasks") or []
            if isinstance(task, dict) and task.get("type") == "tutorial" and task.get("status") == "active"
        ]
        if not tasks:
            return None
        return min(tasks, key=lambda task: int(task.get("globalOrder") or task.get("order") or 0))

    @classmethod
    def _append_tutorial_modification(
        cls, session: dict[str, Any], operation: str, event: dict[str, Any], **details: Any,
    ) -> None:
        entry = {
            "operation": operation,
            "timestamp": int(event.get("timestamp") or cls._now_ms()),
            **{key: value for key, value in details.items() if value not in (None, "")},
        }
        log = session.setdefault("modificationLog", [])
        if entry not in log[-10:]:
            log.append(entry)
        session["modificationLog"] = log[-200:]

    @classmethod
    def _apply_tutorial_progress(cls, context: dict[str, Any], event: dict[str, Any]) -> list[str]:
        event_type = str(event.get("type") or "")
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        now = int(event.get("timestamp") or cls._now_ms())
        session = context.setdefault("tutorialSession", cls._default_tutorial_session(now))
        bindings = session.setdefault("bindings", cls._default_tutorial_session(now)["bindings"])

        # Session lifecycle events are accepted independently of the current tutorial step.
        if event_type == "tutorial_baseline_captured" and event.get("success"):
            baseline_json = str(details.get("baselineJson") or "")
            if baseline_json:
                try:
                    baseline = json.loads(baseline_json)
                except (TypeError, ValueError, json.JSONDecodeError):
                    baseline = None
                if isinstance(baseline, dict):
                    session["baseline"] = cls._merge_baseline(session.get("baseline"), baseline)
            return []
        if event_type == "tutorial_completion_notice_dismissed":
            if session.get("status") == "completed":
                session["completionNoticeExpiresAt"] = 0
            return []
        if event_type == "tutorial_restore_retry_requested":
            if session.get("status") == "restore_failed":
                session["status"] = "restoring"
                session["lastRestoreError"] = ""
            return []
        if event_type == "tutorial_restore_failed":
            session["status"] = "restore_failed"
            session["lastRestoreError"] = cls._detail_text(details, "error", "restoreError")[:2000]
            session["completionNoticeExpiresAt"] = 0
            return []
        if event_type == "tutorial_restore_succeeded" and event.get("success"):
            session["status"] = "completed"
            session["restoredAt"] = now
            session["lastRestoreError"] = ""
            session["completionNoticeExpiresAt"] = now + 15000
            session["modificationLog"] = []
            return []

        if not event.get("success") or session.get("status") != "active":
            return []
        task = cls._active_tutorial_task(context)
        if not task:
            return []
        task_key = str(task.get("taskKey") or "")
        matched = False

        actor_name = cls._detail_text(details, "actorName", "objectName", "modelActorName")
        actor_id = cls._detail_text(details, "actorId", "objectId", "modelActorId")
        bound_actor_name = str(bindings.get("modelActorName") or "")
        bound_actor_id = str(bindings.get("modelActorId") or "")
        actor_matches = bool((bound_actor_id and actor_id == bound_actor_id) or (bound_actor_name and actor_name == bound_actor_name))
        node_id = cls._detail_text(details, "nodeId")
        edge_id = cls._detail_text(details, "edgeId")
        block_id = cls._detail_text(details, "blockId")
        axis = cls._detail_text(details, "axis").lower()
        value = cls._detail_number(details, "value", "newValue")

        if task_key == "tutorial.basics.viewport_focus":
            matched = event_type == "viewport_focused"
        elif task_key == "tutorial.basics.camera_forward_back":
            delta = cls._detail_number(details, "actualDelta", "distance", "delta")
            matched = event_type == "camera_moved" and str(details.get("axisGroup") or "") == "forward_back" and str(details.get("key") or "").upper() in {"W", "S"} and abs(delta or 0) > 1e-6
        elif task_key == "tutorial.basics.camera_left_right":
            delta = cls._detail_number(details, "actualDelta", "distance", "delta")
            matched = event_type == "camera_moved" and str(details.get("axisGroup") or "") == "left_right" and str(details.get("key") or "").upper() in {"A", "D"} and abs(delta or 0) > 1e-6
        elif task_key == "tutorial.basics.camera_up_down":
            delta = cls._detail_number(details, "actualDelta", "distance", "delta")
            matched = event_type == "camera_moved" and str(details.get("axisGroup") or "") == "up_down" and str(details.get("key") or "").upper() in {"Q", "E"} and abs(delta or 0) > 1e-6
        elif task_key == "tutorial.basics.camera_rotate":
            delta = cls._detail_number(details, "actualDelta", "rotationDelta", "delta")
            matched = event_type == "camera_rotated" and details.get("interaction") == "right_mouse_drag" and abs(delta or 0) > 1e-6
        elif task_key == "tutorial.basics.camera_wheel":
            delta = cls._detail_number(details, "actualDelta", "distance", "delta")
            matched = event_type == "camera_moved" and details.get("interaction") == "wheel" and abs(delta or 0) > 1e-6
        elif task_key == "tutorial.basics.open_scene_manager":
            matched = event_type == "panel_opened" and details.get("panelId") == "SceneTools" and details.get("source") == "user"
        elif task_key == "tutorial.basics.import_model":
            matched = event_type == "model_imported" and bool(actor_name or actor_id)
            if matched:
                bindings["sceneName"] = cls._detail_text(details, "sceneName")
                bindings["modelActorName"] = actor_name
                bindings["modelActorId"] = actor_id
                bindings["modelResourcePath"] = cls._detail_text(details, "resourcePath")
                cls._append_tutorial_modification(session, "model_imported", event, sceneName=bindings["sceneName"], actorName=actor_name, actorId=actor_id, resourcePath=bindings["modelResourcePath"])
        elif task_key == "tutorial.basics.select_model":
            matched = event_type == "actor_selected" and actor_matches and details.get("source") in {None, "", "user", "scene_tree", "viewport"}
        elif task_key == "tutorial.basics.set_position_x":
            matched = event_type == "transform_position" and actor_matches and axis == "x" and value is not None and abs(value - 1.0) <= cls.TUTORIAL_VALUE_TOLERANCE
        elif task_key == "tutorial.basics.set_rotation_y":
            matched = event_type == "transform_rotation" and actor_matches and axis == "y" and value is not None and abs(value - 45.0) <= cls.TUTORIAL_ROTATION_TOLERANCE
        elif task_key == "tutorial.basics.set_scale_x":
            matched = event_type == "transform_scale" and actor_matches and axis == "x" and value is not None and abs(value - 1.5) <= cls.TUTORIAL_VALUE_TOLERANCE
        elif task_key == "tutorial.basics.enable_physics":
            enabled = cls._detail_bool(details, "value", "newValue", "enabled")
            matched = event_type == "physics_changed" and actor_matches and details.get("operation") == "SetPhysicsEnabled" and enabled is True
        elif task_key == "tutorial.basics.set_mass":
            matched = event_type == "physics_changed" and actor_matches and details.get("operation") == "SetMass" and value is not None and abs(value - 10.0) <= cls.TUTORIAL_VALUE_TOLERANCE
        elif task_key == "tutorial.basics.set_light_x":
            matched = event_type == "lighting_changed" and axis == "x" and value is not None and abs(value - 0.5) <= cls.TUTORIAL_VALUE_TOLERANCE
            if matched:
                cls._append_tutorial_modification(session, "lighting_changed", event, sceneName=cls._detail_text(details, "sceneName"), axis=axis, value=value)
        elif task_key == "tutorial.basics.open_nodes":
            matched = event_type == "panel_opened" and details.get("panelId") == "NodeGraphPanel" and details.get("source") == "user"
        elif task_key == "tutorial.basics.confirm_start_node":
            node_type = str(details.get("nodeType") or "").lower()
            unique_start = cls._detail_bool(details, "uniqueStart") is True or int(cls._detail_number(details, "startNodeCount") or 0) == 1
            matched = event_type in {"node_created", "node_selected"} and node_type == "start" and bool(node_id) and unique_start
            if matched:
                bindings["startNodeId"] = node_id
                created = event_type == "node_created"
                bindings["startNodeCreatedByTutorial"] = created
                if created:
                    cls._append_tutorial_modification(session, "node_created", event, nodeId=node_id, nodeType="start")
        elif task_key == "tutorial.basics.create_custom_node":
            matched = event_type == "node_created" and str(details.get("nodeType") or "").lower() == "custom" and bool(node_id)
            if matched:
                bindings["customNodeId"] = node_id
                cls._append_tutorial_modification(session, "node_created", event, nodeId=node_id, nodeType="custom")
        elif task_key == "tutorial.basics.move_custom_node":
            delta = cls._detail_number(details, "actualDelta", "distance", "delta")
            matched = event_type == "node_moved" and node_id == bindings.get("customNodeId") and (delta is None or abs(delta) > 1e-6)
        elif task_key == "tutorial.basics.connect_nodes":
            source_id = cls._detail_text(details, "sourceNodeId")
            target_id = cls._detail_text(details, "targetNodeId")
            matched = event_type == "node_connected" and source_id == bindings.get("startNodeId") and target_id == bindings.get("customNodeId") and bool(edge_id)
            if matched:
                bindings["edgeId"] = edge_id
                cls._append_tutorial_modification(session, "edge_created", event, edgeId=edge_id, sourceNodeId=source_id, targetNodeId=target_id)
        elif task_key == "tutorial.basics.open_custom_node":
            matched = event_type == "node_selected" and node_id == bindings.get("customNodeId") and details.get("source") in {None, "", "user"}
        elif task_key == "tutorial.basics.add_when_enter":
            matched = event_type == "block_added" and node_id == bindings.get("customNodeId") and details.get("blockType") == "node_when_enter" and bool(block_id)
            if matched:
                bindings["whenEnterBlockId"] = block_id
                cls._append_tutorial_modification(session, "block_created", event, nodeId=node_id, blockId=block_id, blockType="node_when_enter")
        elif task_key == "tutorial.basics.add_wait":
            matched = event_type in {"block_added", "block_connected"} and node_id == bindings.get("customNodeId") and details.get("blockType") == "control_wait" and details.get("parentBlockType") == "node_when_enter" and cls._detail_bool(details, "connected") is True and bool(block_id)
            if matched:
                bindings["waitBlockId"] = block_id
                cls._append_tutorial_modification(session, "block_created", event, nodeId=node_id, blockId=block_id, blockType="control_wait")
        elif task_key == "tutorial.basics.set_wait_seconds":
            new_value = cls._detail_number(details, "newValue", "value")
            matched = event_type == "block_parameter_changed" and block_id == bindings.get("waitBlockId") and details.get("blockType") == "control_wait" and str(details.get("fieldName") or "").upper() == "SECONDS" and new_value is not None and abs(new_value - 2.0) <= cls.TUTORIAL_VALUE_TOLERANCE
        elif task_key == "tutorial.basics.select_edge":
            matched = event_type == "edge_selected" and edge_id == bindings.get("edgeId") and details.get("source") in {None, "", "user"}
        elif task_key == "tutorial.basics.add_true_condition":
            bool_value = cls._detail_bool(details, "newValue", "value")
            matched = event_type in {"block_added", "block_connected", "block_parameter_changed"} and edge_id == bindings.get("edgeId") and details.get("workspaceRole") == "condition" and details.get("blockType") == "logic_boolean" and bool_value is True and bool(block_id)
            if matched:
                bindings["conditionBlockId"] = block_id
                cls._append_tutorial_modification(session, "block_created", event, edgeId=edge_id, blockId=block_id, blockType="logic_boolean")
        elif task_key == "tutorial.basics.run_graph":
            matched = event_type == "run_succeeded"
        elif task_key == "tutorial.basics.start_preview":
            matched = event_type == "preview_started" and str(details.get("status") or "running") == "running"
        elif task_key == "tutorial.basics.stop_preview":
            stopped = str(details.get("status") or "stopped") == "stopped"
            restored = cls._detail_bool(details, "restored", "sceneRestored") is True
            restore_error = cls._detail_text(details, "restoreError", "error")
            matched = event_type == "preview_stopped" and stopped and restored and not restore_error

        if not matched or not cls._complete_task_locked(context, task_key, now):
            return []
        if task_key == "tutorial.basics.stop_preview":
            session["status"] = "restoring"
            session["lastRestoreError"] = ""
            session["completionNoticeExpiresAt"] = 0
        return [task_key]

    @classmethod
    def _goal_signals_for_event(cls, event: dict[str, Any]) -> set[str]:
        if not event.get("success"):
            return set()
        event_type = str(event.get("type") or "")
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        signals: set[str] = set()
        if event_type in {"model_imported", "actor_created"}:
            signals.add("model_imported")
        if event_type in {"transform_position", "transform_rotation", "transform_scale"}:
            signals.add("object_transformed")
        if event_type == "lighting_changed":
            signals.add("lighting_adjusted")
        if event_type == "physics_changed":
            signals.add("physics_adjusted")
        if event_type == "node_created":
            signals.add("node_created")
        if event_type == "node_moved":
            signals.add("node_moved")
        if event_type == "node_connected":
            source = str(details.get("sourceNodeId") or "")
            target = str(details.get("targetNodeId") or "")
            if source and target and source != target:
                signals.add("nodes_connected")
        if event_type == "block_added":
            signals.add("block_added")
            if details.get("workspaceRole") == "condition":
                signals.add("transition_condition_set")
        if event_type == "block_parameter_changed":
            signals.add("block_parameter_changed")
        if event_type in {"run_started", "run_succeeded"}:
            signals.add("node_graph_run")
        if event_type == "run_succeeded":
            signals.add("run_succeeded")
        return signals

    @classmethod
    def _apply_goal_progress(cls, context: dict[str, Any], event: dict[str, Any]) -> list[str]:
        signals = cls._goal_signals_for_event(event)
        if not signals:
            return []
        counts = context.setdefault("goalSignalCounts", {})
        for signal in signals:
            counts[signal] = int(counts.get(signal) or 0) + 1

        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        block_type = str(details.get("blockType") or "").strip()
        now = int(event.get("timestamp") or cls._now_ms())
        completed: list[str] = []
        for task in list(context.get("activeTasks") or []):
            if not isinstance(task, dict) or task.get("type") != "goal":
                continue
            if task.get("status") not in {"active", "pending"}:
                continue
            signal = str(task.get("completionSignal") or "")
            if signal not in signals:
                continue

            required_block_types = {
                str(item).strip()
                for item in task.get("requiredBlockTypes") or []
                if str(item).strip()
            }
            if required_block_types:
                if not block_type or block_type not in required_block_types:
                    continue
                observed = {
                    str(item).strip()
                    for item in task.get("observedBlockTypes") or []
                    if str(item).strip()
                }
                observed.add(block_type)
                task["observedBlockTypes"] = sorted(observed)
                task["updatedAt"] = now
                if not required_block_types.issubset(observed):
                    continue
            else:
                required = max(1, int(task.get("requiredCount") or 1))
                if int(counts.get(signal) or 0) < required:
                    continue

            task_key = str(task.get("taskKey") or "")
            if task_key and cls._complete_task_locked(context, task_key, now):
                completed.append(task_key)
        return completed

    def record_event(self, payload: Any) -> dict[str, Any]:
        try:
            event = self._normalize_event(payload)
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            with self._lock:
                context = self._read_locked(project_path)
                context["recentOperationEvents"].append(event)
                context["recentOperationEvents"] = context["recentOperationEvents"][-self.MAX_RECENT_EVENTS :]
                metric = self.METRIC_BY_EVENT.get(event["type"])
                if metric and event["success"]:
                    context["metrics"][metric] = int(context["metrics"].get(metric) or 0) + 1
                if event["type"] in self.IMPORTANT_EVENT_TYPES and event["success"]:
                    context["metrics"]["importantEventCount"] = int(context["metrics"].get("importantEventCount") or 0) + 1
                if not context["metrics"].get("firstActivityAt"):
                    context["metrics"]["firstActivityAt"] = event["timestamp"]
                context["metrics"]["lastActivityAt"] = event["timestamp"]
                completed = self._apply_tutorial_progress(context, event)
                completed.extend(self._apply_goal_progress(context, event))
                self._ensure_task_slots_locked(context, event["timestamp"])
                for task_key in completed:
                    completed_task = next(
                        (
                            task for task in reversed(context["taskHistory"])
                            if isinstance(task, dict) and task.get("taskKey") == task_key
                        ),
                        {},
                    )
                    completed_type = str(completed_task.get("type") or "")
                    completion_event_type = (
                        "goal_task_completed" if completed_type == "goal" else "tutorial_completed"
                    )
                    context["recentOperationEvents"].append({
                        "eventId": f"event_{uuid.uuid4().hex}",
                        "type": completion_event_type,
                        "category": "assistant",
                        "success": True,
                        "timestamp": event["timestamp"],
                        "details": {"taskKey": task_key, "taskType": completed_type},
                    })
                self._write_locked(project_path, context)
                return {
                    "success": True,
                    "status": "ok",
                    "completedTaskKeys": completed,
                    "context": self._clone(context),
                }
        except ValueError as exc:
            return self._error("INVALID_CONTEXT_EVENT", str(exc))
        except Exception as exc:
            logger.warning("Unable to record Cabbage event: %s", exc)
            return self._error("CONTEXT_WRITE_FAILED", str(exc))

    @classmethod
    def _normalize_task(cls, payload: Any) -> tuple[str, dict[str, Any]]:
        if not isinstance(payload, dict):
            raise ValueError("包菜任务格式不正确")
        action = str(payload.get("action") or "upsert").strip()
        raw = payload.get("task") if isinstance(payload.get("task"), dict) else payload
        task_key = str(raw.get("taskKey") or raw.get("issueKey") or raw.get("code") or "").strip()[:180]
        if not task_key:
            raise ValueError("包菜任务缺少 taskKey")
        now = cls._now_ms()
        raw_type = str(raw.get("type") or "node-issue")
        task_type = raw_type if raw_type in {"tutorial", "goal", "node-issue"} else "node-issue"

        def english_field(name: str, source_name: str, fallback: str = "") -> str:
            english = str(raw.get(name) or "").strip()
            source = str(raw.get(source_name) or "").strip()
            if not english:
                return fallback
            if english == source and any("\u3400" <= char <= "\u9fff" for char in english):
                return fallback
            return english
        task = {
            "taskKey": task_key,
            "issueKey": task_key,
            "type": task_type,
            "track": str(raw.get("track") or "")[:40],
            "order": int(raw.get("order") or 0),
            "status": str(raw.get("status") or ("candidate" if action == "candidate" else "active"))[:40],
            "code": str(raw.get("code") or task_key)[:180],
            "severity": str(raw.get("severity") or "warning")[:40],
            "confidence": float(raw.get("confidence") or 0),
            "nodeId": str(raw.get("nodeId") or "")[:180],
            "blockId": str(raw.get("blockId") or "")[:180],
            "edgeId": str(raw.get("edgeId") or "")[:180],
            "pattern": cls._normalize_issue_pattern(raw.get("pattern")),
            "title": str(raw.get("title") or "节点逻辑需要调整").strip()[:160],
            "titleEn": english_field(
                "titleEn",
                "title",
                "Node Logic Needs Adjustment" if not raw.get("title") and task_type == "node-issue" else "",
            )[:160],
            "message": str(raw.get("message") or "").strip()[:1600],
            "messageEn": english_field("messageEn", "message")[:1600],
            "suggestion": str(raw.get("suggestion") or "").strip()[:1600],
            "suggestionEn": english_field("suggestionEn", "suggestion")[:1600],
            "completionCriteria": str(raw.get("completionCriteria") or "").strip()[:800],
            "completionCriteriaEn": english_field("completionCriteriaEn", "completionCriteria")[:800],
            "completionSignal": str(raw.get("completionSignal") or "").strip()[:80],
            "requiredCount": max(1, int(raw.get("requiredCount") or 1)),
            "phase": str(raw.get("phase") or "").strip()[:40],
            "effectId": str(raw.get("effectId") or "").strip()[:120],
            "requiredBlockTypes": [
                str(item).strip()[:180]
                for item in (raw.get("requiredBlockTypes") or [])
                if str(item).strip()
            ][:20],
            "observedBlockTypes": [
                str(item).strip()[:180]
                for item in (raw.get("observedBlockTypes") or [])
                if str(item).strip()
            ][:20],
            "guidanceIntent": str(raw.get("guidanceIntent") or "").strip()[:80],
            "graphRevision": str(raw.get("graphRevision") or "")[:180],
            "createdAt": int(raw.get("createdAt") or now),
            "firstDetectedAt": int(raw.get("firstDetectedAt") or raw.get("createdAt") or now),
            "updatedAt": now,
            "completedAt": int(raw.get("completedAt") or 0),
            "resolvedAt": int(raw.get("resolvedAt") or 0),
        }
        return action, task

    @classmethod
    def _append_internal_event_locked(
        cls,
        context: dict[str, Any],
        event_type: str,
        *,
        task_key: str,
        timestamp: int,
    ) -> None:
        event = {
            "eventId": f"event_{uuid.uuid4().hex}",
            "type": event_type,
            "category": "node",
            "success": True,
            "timestamp": timestamp,
            "details": {"taskKey": task_key},
        }
        context["recentOperationEvents"].append(event)
        context["recentOperationEvents"] = context["recentOperationEvents"][-cls.MAX_RECENT_EVENTS :]
        context["metrics"]["importantEventCount"] = int(context["metrics"].get("importantEventCount") or 0) + 1
        if not context["metrics"].get("firstActivityAt"):
            context["metrics"]["firstActivityAt"] = timestamp
        context["metrics"]["lastActivityAt"] = timestamp

    def update_task(self, payload: Any) -> dict[str, Any]:
        try:
            action, incoming = self._normalize_task(payload)
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            now = self._now_ms()
            with self._lock:
                context = self._read_locked(project_path)
                existing = self._find_task(context, incoming["taskKey"])
                if action in {"complete", "resolve", "cancel"}:
                    if existing:
                        context["activeTasks"].remove(existing)
                        archived = dict(existing)
                        archived.update(incoming)
                        archived["status"] = {"complete": "completed", "resolve": "resolved", "cancel": "cancelled"}[action]
                        archived["updatedAt"] = now
                        if action == "complete":
                            archived["completedAt"] = now
                        else:
                            archived["resolvedAt"] = now
                        context["taskHistory"].append(archived)
                        if existing.get("type") in {"tutorial", "goal"}:
                            self._ensure_task_slots_locked(context, now)
                        if existing.get("type") == "node-issue" and action == "resolve":
                            context["metrics"]["nodeIssueFixes"] = int(context["metrics"].get("nodeIssueFixes") or 0) + 1
                            memory = self._issue_memory_entry_locked(context, str(existing.get("code") or incoming.get("code") or ""))
                            memory["resolvedCount"] = int(memory.get("resolvedCount") or 0) + 1
                            self._append_internal_event_locked(
                                context,
                                "node_issue_fixed",
                                task_key=incoming["taskKey"],
                                timestamp=now,
                            )
                    self._write_locked(project_path, context)
                    return {"success": True, "status": "ok", "context": self._clone(context)}

                if existing:
                    created_at = int(existing.get("createdAt") or incoming["createdAt"])
                    first_detected = int(existing.get("firstDetectedAt") or incoming["firstDetectedAt"])
                    existing.update(incoming)
                    existing["createdAt"] = created_at
                    existing["firstDetectedAt"] = first_detected
                    if incoming["type"] == "node-issue":
                        memory = self._issue_memory_entry_locked(context, incoming.get("code") or incoming["taskKey"])
                        memory["pattern"].update(incoming.get("pattern") or {})
                else:
                    if incoming["type"] == "node-issue":
                        # Update memory before inserting the task. When an older context has
                        # no issueMemory yet, normalization reconstructs it from existing
                        # tasks; inserting first would count this first occurrence twice.
                        context["metrics"]["nodeErrors"] = int(context["metrics"].get("nodeErrors") or 0) + 1
                        memory = self._issue_memory_entry_locked(context, incoming.get("code") or incoming["taskKey"])
                        memory["occurrences"] = int(memory.get("occurrences") or 0) + 1
                        memory["firstSeenAt"] = int(memory.get("firstSeenAt") or now)
                        memory["lastSeenAt"] = now
                        memory["pattern"].update(incoming.get("pattern") or {})
                        self._append_internal_event_locked(
                            context,
                            "node_issue_found",
                            task_key=incoming["taskKey"],
                            timestamp=now,
                        )
                    context["activeTasks"].append(incoming)
                self._write_locked(project_path, context)
                return {"success": True, "status": "ok", "context": self._clone(context)}
        except ValueError as exc:
            return self._error("INVALID_CONTEXT_TASK", str(exc))
        except Exception as exc:
            logger.warning("Unable to update Cabbage task: %s", exc)
            return self._error("CONTEXT_WRITE_FAILED", str(exc))

    def append_message(self, payload: Any) -> dict[str, Any]:
        try:
            if not isinstance(payload, dict):
                raise ValueError("包菜消息格式不正确")
            content = str(payload.get("content") or "").strip()[:12000]
            if not content:
                raise ValueError("包菜消息内容为空")
            message = {
                "id": str(payload.get("id") or f"cabbage_msg_{uuid.uuid4().hex}"),
                "role": "assistant" if payload.get("role") == "assistant" else "user",
                "content": content,
                "createdAt": int(payload.get("createdAt") or self._now_ms()),
                "taskKey": str(payload.get("taskKey") or "").strip()[:180],
                "issueCode": str(payload.get("issueCode") or "").strip()[:180],
                "nodeId": str(payload.get("nodeId") or "").strip()[:180],
                "blockId": str(payload.get("blockId") or "").strip()[:180],
                "needsShowcase": payload.get("needsShowcase") is True,
                "guidanceIntent": str(payload.get("guidanceIntent") or "").strip()[:80],
                "steps": [
                    str(step or "").strip()[:500]
                    for step in (payload.get("steps") if isinstance(payload.get("steps"), list) else [])[:8]
                    if str(step or "").strip()
                ],
            }
            if message["guidanceIntent"] not in self.CHAT_GUIDANCE_INTENTS:
                message["guidanceIntent"] = ""
                message["needsShowcase"] = False
            if not message["guidanceIntent"]:
                message["needsShowcase"] = False
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            with self._lock:
                context = self._read_locked(project_path)
                if not message["issueCode"] and message["taskKey"]:
                    related = self._find_task(context, message["taskKey"]) or next(
                        (task for task in reversed(context["taskHistory"])
                         if isinstance(task, dict) and task.get("taskKey") == message["taskKey"]),
                        None,
                    )
                    if related and related.get("type") == "node-issue":
                        message["issueCode"] = str(related.get("code") or "")[:180]
                        message["nodeId"] = message["nodeId"] or str(related.get("nodeId") or "")[:180]
                        message["blockId"] = message["blockId"] or str(related.get("blockId") or "")[:180]
                is_new = not any(item.get("id") == message["id"] for item in context["chatMessages"] if isinstance(item, dict))
                if is_new:
                    context["chatMessages"].append(message)
                    if message["role"] == "user" and message["issueCode"]:
                        memory = self._issue_memory_entry_locked(context, message["issueCode"])
                        memory["chatDiscussionCount"] = int(memory.get("chatDiscussionCount") or 0) + 1
                        memory["lastDiscussedAt"] = message["createdAt"]
                self._write_locked(project_path, context)
                return {
                    "success": True,
                    "status": "ok",
                    "message": message,
                    "context": self._clone(context),
                }
        except ValueError as exc:
            return self._error("INVALID_CONTEXT_MESSAGE", str(exc))
        except Exception as exc:
            logger.warning("Unable to append Cabbage message: %s", exc)
            return self._error("CONTEXT_WRITE_FAILED", str(exc))

    @classmethod
    def _goal_block_catalog(cls) -> list[dict[str, str]]:
        catalog = NodeGraphReviewService._catalog_index()
        return [
            {
                "type": str(item.get("type") or ""),
                "category": str(item.get("category") or ""),
                "label": str(item.get("label") or ""),
                "shape": str(item.get("shape") or ""),
                "outputCheck": str(item.get("outputCheck") or ""),
                "projectUsage": str(item.get("projectUsage") or ""),
            }
            for item in catalog.values()
            if item.get("type") and item.get("projectUsage") == "project-safe"
        ]

    @classmethod
    def _goal_plan_prompt(cls, world_prompt: str, mode: str) -> str:
        capabilities = {
            "model_imported": "导入一个模型或在场景中新建模型对象",
            "object_transformed": "修改一个对象的位置、旋转或缩放",
            "lighting_adjusted": "修改场景光照开关或光照方向",
            "physics_adjusted": "修改一个对象的物理、碰撞、质量、弹性或阻尼",
            "node_created": "创建一个节点",
            "node_moved": "拖动一个节点",
            "nodes_connected": "连接两个不同节点",
            "block_added": "向节点内加入指定类型的积木",
            "block_parameter_changed": "修改指定类型积木的参数",
            "transition_condition_set": "为节点连线设置一个 Boolean 条件",
            "node_graph_run": "发起一次节点逻辑运行",
            "run_succeeded": "节点逻辑成功运行",
        }
        schema = {
            "logicBlueprint": {
                "worldSummary": "",
                "coreLoop": "",
                "requiredActors": [],
                "nodeEffects": [
                    {
                        "effectId": "effect_01",
                        "title": "",
                        "description": "",
                        "trigger": "",
                        "outcome": "",
                        "recommendedBlockTypes": [],
                        "verification": "",
                    }
                ],
                "flow": [],
            },
            "tasks": [
                {
                    "phase": "node-logic",
                    "effectId": "effect_01",
                    "title": "",
                    "titleEn": "",
                    "message": "",
                    "messageEn": "",
                    "suggestion": "",
                    "suggestionEn": "",
                    "completionCriteria": "",
                    "completionCriteriaEn": "",
                    "completionSignal": "block_added",
                    "requiredBlockTypes": [],
                }
            ],
        }
        request_context = {
            "mode": mode,
            "description": world_prompt,
        }
        return (
            "你是 CoronaEngine 3D 游戏编辑器的世界搭建任务规划器。"
            "用户的 description 可以是任意语言、任意题材、任意详细程度的自然语言，必须把它作为本次规划唯一的世界语义来源。"
            "只分析 description 中实际出现或能够直接推导出的场景、对象、体验、交互和目标，形成 logicBlueprint。"
            "如果描述偏抽象、偏氛围或没有明确玩法，就把其中的视觉与体验目标拆成当前引擎能够验证的场景任务和最小交互任务；"
            "不得擅自加入 description 未包含且不能直接推导出的具体角色、道具、机关、运动方式、交互、战斗、胜负条件或其他固定玩法。"
            "不得使用固定题材模板或按关键词套用预制任务，也不得照抄返回结构模板中的 effect_01。"
            "logicBlueprint 只是理解世界目标的内部分析，不是节点图、不是积木 JSON，也不能直接修改当前节点区。"
            "最终产物只能是一套与当前 description 强相关的个性化搭建任务，由任务一步一步引导用户亲自完成世界。"
            "生成 6 到 10 个循序渐进的任务。目标是先让当前世界所需的节点玩法逻辑成立，再完成必要的场景内容和表现，而不是替用户生成一套节点积木。"
            "至少 5 个任务必须是 phase=node-logic，并且所有 node-logic 任务必须排在 scene-polish 前。"
            "每个任务只能对应一个可由 completionSignal 验证的操作目标；不要把光照和物理、导入和变换等不同完成信号合并在同一个任务中。"
            "每个任务的 title、message、suggestion、completionCriteria 必须使用简体中文，"
            "并同时提供语义一致、自然简洁的英文 titleEn、messageEn、suggestionEn、completionCriteriaEn。"
            "如果一个玩法效果需要多个积木，可以在同一个积木任务的 requiredBlockTypes 中列出，但标题、说明和完成条件必须与该单一任务目标一致。"
            "节点任务必须围绕当前 description 真正需要的效果组织；能力目录中的输入、移动、碰撞等只代表可选能力，不是必须加入世界的内容。"
            "禁止使用‘随便创建节点’‘任意拖入积木’这类脱离世界目标的通用教程。"
            "最后一个 node-logic 任务必须使用 run_succeeded，确认前面的玩法节点能够成功运行。"
            "scene-polish 只能放在节点逻辑验证之后，用于当前 description 确实需要的模型、变换、光照或物理准备。"
            "requiredActors 可以填写角色、普通物体、场景区域或系统，但只能来自当前 description 的需求。"
            "nodeEffects.recommendedBlockTypes 与 tasks.requiredBlockTypes 只能从下方 XML 积木目录选择，必须使用精确 type，不能编造。"
            "completionSignal 为 block_added 或 block_parameter_changed 时必须给出 requiredBlockTypes；其他完成信号不要填写该数组。"
            "每个任务只使用一个 completionSignal。不要输出 Python、脚本、XML 或 Markdown，只输出合法 JSON。\n"
            "返回结构模板（仅表示字段结构，空数组必须按当前 description 补全，示例标识不能照抄）："
            + json.dumps(schema, ensure_ascii=False, separators=(",", ":")) + "\n"
            "本次用户输入数据："
            + json.dumps(request_context, ensure_ascii=False, separators=(",", ":")) + "\n"
            "可用完成信号：" + json.dumps(capabilities, ensure_ascii=False, separators=(",", ":")) + "\n"
            "可用的项目级积木目录：" + json.dumps(cls._goal_block_catalog(), ensure_ascii=False, separators=(",", ":"))
        )

    @classmethod
    def _call_deepseek_for_goal_plan(cls, world_prompt: str, mode: str) -> dict[str, Any]:
        settings = NodeGraphReviewService._resolve_settings()
        if not settings.api_key:
            raise ValueError("DeepSeek API Key 未配置，无法生成世界任务")
        base = settings.base_url.rstrip("/")
        endpoint = base if base.endswith("/chat/completions") else base + "/chat/completions"
        body = {
            "model": settings.model,
            "temperature": 0.25,
            "max_tokens": 3600,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "messages": [
                {
                    "role": "system",
                    "content": "你只负责为 CoronaEngine 生成结构化的个性化世界搭建任务，绝不生成或修改节点图、积木工作区和脚本，必须返回合法 JSON。",
                },
                {"role": "user", "content": cls._goal_plan_prompt(world_prompt, mode)},
            ],
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + settings.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=cls.GOAL_PLAN_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        choices = payload.get("choices") if isinstance(payload, dict) else None
        message = choices[0].get("message") if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("DeepSeek 没有返回世界任务")
        return NodeGraphReviewService._parse_model_result(content)

    @classmethod
    def _normalize_block_type_list(cls, raw: Any, *, field_name: str) -> list[str]:
        if raw in (None, ""):
            return []
        if not isinstance(raw, list):
            raise ValueError(f"DeepSeek 世界任务中的 {field_name} 必须是数组")
        catalog = NodeGraphReviewService._catalog_index()
        normalized: list[str] = []
        for item in raw:
            block_type = str(item or "").strip()[:180]
            if not block_type or block_type in normalized:
                continue
            block = catalog.get(block_type)
            if not block or block.get("projectUsage") != "project-safe":
                raise ValueError(f"DeepSeek 返回了不存在或不适用于项目节点图的积木：{block_type}")
            normalized.append(block_type)
        return normalized[:20]

    @classmethod
    def _normalize_logic_blueprint(cls, result: dict[str, Any]) -> dict[str, Any]:
        raw = result.get("logicBlueprint") if isinstance(result, dict) else None
        if not isinstance(raw, dict):
            raise ValueError("DeepSeek 世界任务结果缺少 logicBlueprint")
        world_summary = str(raw.get("worldSummary") or "").strip()[:800]
        core_loop = str(raw.get("coreLoop") or "").strip()[:1200]
        if not world_summary or not core_loop:
            raise ValueError("DeepSeek 世界玩法蓝图缺少世界概述或核心循环")

        actors = [
            str(item).strip()[:160]
            for item in (raw.get("requiredActors") or [])
            if str(item).strip()
        ][:30]
        flow = [
            str(item).strip()[:240]
            for item in (raw.get("flow") or [])
            if str(item).strip()
        ][:20]
        if not actors or len(flow) < 3:
            raise ValueError("DeepSeek 世界玩法蓝图缺少角色清单或节点流程")

        raw_effects = raw.get("nodeEffects")
        if not isinstance(raw_effects, list):
            raise ValueError("DeepSeek 世界玩法蓝图缺少 nodeEffects")
        effects: list[dict[str, Any]] = []
        effect_ids: set[str] = set()
        for item in raw_effects[:16]:
            if not isinstance(item, dict):
                continue
            effect_id = str(item.get("effectId") or "").strip()[:120]
            title = str(item.get("title") or "").strip()[:200]
            description = str(item.get("description") or "").strip()[:1200]
            verification = str(item.get("verification") or "").strip()[:800]
            if not effect_id or effect_id in effect_ids or not title or not description or not verification:
                raise ValueError("DeepSeek 世界玩法蓝图中的节点效果字段不完整或 effectId 重复")
            recommended = cls._normalize_block_type_list(
                item.get("recommendedBlockTypes"), field_name="recommendedBlockTypes",
            )
            if not recommended:
                raise ValueError(f"节点效果 {effect_id} 没有对应的现有积木")
            effect_ids.add(effect_id)
            effects.append({
                "effectId": effect_id,
                "title": title,
                "description": description,
                "trigger": str(item.get("trigger") or "").strip()[:800],
                "outcome": str(item.get("outcome") or "").strip()[:800],
                "recommendedBlockTypes": recommended,
                "verification": verification,
            })
        if len(effects) < 2:
            raise ValueError("DeepSeek 世界玩法蓝图中的节点效果数量不足")
        return {
            "worldSummary": world_summary,
            "coreLoop": core_loop,
            "requiredActors": actors,
            "nodeEffects": effects,
            "flow": flow,
        }

    @classmethod
    def _normalize_goal_plan_tasks(
        cls,
        result: dict[str, Any],
        context: dict[str, Any],
        now: int,
    ) -> list[dict[str, Any]]:
        blueprint = cls._normalize_logic_blueprint(result)
        effect_ids = {str(item.get("effectId") or "") for item in blueprint["nodeEffects"]}
        raw_tasks = result.get("tasks") if isinstance(result, dict) else None
        if not isinstance(raw_tasks, list):
            raise ValueError("DeepSeek 世界任务结果缺少 tasks 数组")
        raw_tasks = raw_tasks[:10]
        if len(raw_tasks) < 6:
            raise ValueError("DeepSeek 生成的世界任务数量不足")
        guidance_by_signal = {
            "model_imported": "import_model",
            "object_transformed": "transform_model",
            "lighting_adjusted": "adjust_lighting",
            "physics_adjusted": "adjust_physics",
            "node_created": "create_node",
            "node_moved": "move_node",
            "nodes_connected": "connect_nodes",
            "block_added": "drag_block",
            "block_parameter_changed": "edit_block_parameter",
            "transition_condition_set": "set_transition_condition",
            "node_graph_run": "run_node_graph",
            "run_succeeded": "run_node_graph",
        }
        baseline = {
            signal: max(0, int(count or 0))
            for signal, count in (context.get("goalSignalCounts") or {}).items()
            if signal in cls.GOAL_COMPLETION_SIGNALS
        }
        occurrences: dict[str, int] = {}
        tasks: list[dict[str, Any]] = []
        node_task_count = 0
        seen_scene_phase = False
        for index, raw in enumerate(raw_tasks, start=1):
            if not isinstance(raw, dict):
                continue
            phase = str(raw.get("phase") or "").strip()
            if phase not in cls.GOAL_PHASES:
                raise ValueError(f"DeepSeek 返回了不支持的任务阶段：{phase or '(空)'}")
            if phase == "scene-polish":
                seen_scene_phase = True
            elif seen_scene_phase:
                raise ValueError("节点玩法任务必须全部排在场景美化任务之前")

            signal = str(raw.get("completionSignal") or "").strip()
            if signal not in cls.GOAL_COMPLETION_SIGNALS:
                raise ValueError(f"DeepSeek 返回了不支持的完成信号：{signal or '(空)'}")
            if phase == "node-logic" and signal not in cls.GOAL_NODE_SIGNALS:
                raise ValueError("节点玩法任务使用了场景编辑完成信号")
            if phase == "scene-polish" and signal not in cls.GOAL_SCENE_SIGNALS:
                raise ValueError("场景美化任务使用了节点完成信号")

            effect_id = str(raw.get("effectId") or "").strip()[:120]
            if phase == "node-logic":
                node_task_count += 1
                if not effect_id or effect_id not in effect_ids:
                    raise ValueError("节点玩法任务没有关联 logicBlueprint 中的 effectId")
            else:
                effect_id = ""

            required_block_types = cls._normalize_block_type_list(
                raw.get("requiredBlockTypes"), field_name="requiredBlockTypes",
            )
            if signal in {"block_added", "block_parameter_changed"} and not required_block_types:
                raise ValueError("积木任务必须给出 requiredBlockTypes")
            if signal not in {"block_added", "block_parameter_changed"} and required_block_types:
                raise ValueError("非积木任务不应设置 requiredBlockTypes")

            title = str(raw.get("title") or "").strip()[:160]
            message = str(raw.get("message") or "").strip()[:1600]
            suggestion = str(raw.get("suggestion") or "").strip()[:1600]
            criteria = str(raw.get("completionCriteria") or "").strip()[:800]
            title_en = str(raw.get("titleEn") or title).strip()[:160]
            message_en = str(raw.get("messageEn") or message).strip()[:1600]
            suggestion_en = str(raw.get("suggestionEn") or suggestion).strip()[:1600]
            criteria_en = str(raw.get("completionCriteriaEn") or criteria).strip()[:800]
            if not title or not message or not suggestion or not criteria:
                raise ValueError("DeepSeek 生成的世界任务字段不完整")
            occurrences[signal] = occurrences.get(signal, 0) + 1
            tasks.append({
                "taskKey": f"goal.ai.{index:02d}",
                "issueKey": f"goal.ai.{index:02d}",
                "type": "goal",
                "track": "world-goal",
                "phase": phase,
                "effectId": effect_id,
                "order": index,
                "status": "queued",
                "code": "world_goal_step",
                "severity": "info",
                "confidence": 1.0,
                "title": title,
                "titleEn": title_en,
                "message": message,
                "messageEn": message_en,
                "suggestion": suggestion,
                "suggestionEn": suggestion_en,
                "completionCriteria": criteria,
                "completionCriteriaEn": criteria_en,
                "completionSignal": signal,
                "requiredCount": baseline.get(signal, 0) + occurrences[signal],
                "requiredBlockTypes": required_block_types,
                "observedBlockTypes": [],
                "guidanceIntent": guidance_by_signal[signal],
                "createdAt": now,
                "firstDetectedAt": now,
                "updatedAt": now,
                "completedAt": 0,
                "resolvedAt": 0,
            })
        if len(tasks) < 6:
            raise ValueError("DeepSeek 生成的有效世界任务数量不足")
        if node_task_count < cls.MIN_GOAL_NODE_TASKS:
            raise ValueError("世界任务必须优先包含足够的节点玩法实现步骤")
        node_tasks = [task for task in tasks if task.get("phase") == "node-logic"]
        if not node_tasks or node_tasks[-1].get("completionSignal") != "run_succeeded":
            raise ValueError("最后一个节点玩法任务必须验证节点逻辑成功运行")
        return tasks

    def start_goal_plan(self, payload: Any = None) -> dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        prompt = str(payload.get("prompt") or "").strip()[:4000]
        mode = str(payload.get("mode") or "story").strip().lower()
        if mode not in {"story", "creative"}:
            mode = "story"
        try:
            project_path = self._active_project_path()
            self._validate_payload_world(project_path, payload)
            now = self._now_ms()
            with self._lock:
                context = self._read_locked(project_path)
                if not prompt:
                    context["worldGoal"] = {
                        "prompt": "",
                        "mode": mode,
                        "source": "default",
                        "status": "ready",
                        "generatedAt": 0,
                        "generationError": "",
                        "generationId": "",
                    }
                    context["goalTaskPlan"] = {
                        "schemaVersion": 2,
                        "generatedAt": 0,
                        "taskCount": 0,
                        "nodeTaskCount": 0,
                        "sceneTaskCount": 0,
                        "logicBlueprint": {},
                    }
                    context["activeTasks"] = [
                        task for task in context.get("activeTasks") or []
                        if not isinstance(task, dict) or task.get("type") != "goal"
                    ]
                    self._ensure_task_slots_locked(context, now)
                    self._write_locked(project_path, context)
                    return {"success": True, "status": "completed", "context": self._clone(context)}

                goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
                goal_plan_tasks = [
                    task for task in [*(context.get("activeTasks") or []), *(context.get("taskHistory") or [])]
                    if isinstance(task, dict) and task.get("type") == "goal"
                ]
                has_goal_plan = any(
                    all(str(task.get(field) or "").strip() for field in (
                        "titleEn", "messageEn", "suggestionEn", "completionCriteriaEn",
                    ))
                    for task in goal_plan_tasks
                )
                if (goal.get("status") == "ready"
                        and str(goal.get("prompt") or "") == prompt
                        and str(goal.get("mode") or "story") == mode
                        and has_goal_plan):
                    return {"success": True, "status": "completed", "context": self._clone(context)}
                current_generation_id = str(goal.get("generationId") or "")
                current_state = self._goal_plan_tasks.get(current_generation_id)
                if (goal.get("status") == "generating"
                        and goal.get("source") == "ai"
                        and str(goal.get("prompt") or "") == prompt
                        and str(goal.get("mode") or "story") == mode
                        and current_state
                        and current_state.get("status") == "running"
                        and current_state.get("projectPath") == str(project_path)):
                    return {"success": True, "status": "pending", "taskId": current_generation_id}

                task_id = f"cabbage_goal_plan_{uuid.uuid4().hex}"
                context["worldGoal"] = {
                    "prompt": prompt,
                    "mode": mode,
                    "source": "ai",
                    "status": "generating",
                    "generatedAt": 0,
                    "generationError": "",
                    "generationId": task_id,
                }
                context["goalTaskPlan"] = {
                    "schemaVersion": 2,
                    "generatedAt": 0,
                    "taskCount": 0,
                    "nodeTaskCount": 0,
                    "sceneTaskCount": 0,
                    "logicBlueprint": {},
                }
                context["activeTasks"] = [
                    task for task in context.get("activeTasks") or []
                    if not isinstance(task, dict) or task.get("type") != "goal"
                ]
                # Keep the deterministic tutorials visible while DeepSeek is planning.
                # The successful result replaces them atomically; a timeout, crash or
                # invalid AI response therefore never leaves the task board empty.
                self._ensure_task_slots_locked(context, now)
                self._write_locked(project_path, context)
                self._goal_plan_tasks[task_id] = {
                    "taskId": task_id,
                    "status": "running",
                    "projectPath": str(project_path),
                    "prompt": prompt,
                    "mode": mode,
                    "createdAt": time.time(),
                    "result": None,
                }
                self._prune_goal_plan_tasks_locked()
                future = self._executor.submit(self._generate_goal_plan, project_path, prompt, mode, task_id)
                future.add_done_callback(lambda completed, current_task_id=task_id: self._complete_goal_plan(current_task_id, completed))
                return {"success": True, "status": "pending", "taskId": task_id}
        except Exception as exc:
            logger.warning("Unable to start Cabbage world task generation: %s", type(exc).__name__)
            return self._error("GOAL_PLAN_START_FAILED", str(exc))

    def _generate_goal_plan(
        self, project_path: Path, prompt: str, mode: str, generation_id: str,
    ) -> dict[str, Any]:
        try:
            result = self._call_deepseek_for_goal_plan(prompt, mode)
            now = self._now_ms()
            with self._lock:
                context = self._read_locked(project_path)
                current_goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
                if (str(current_goal.get("prompt") or "") != prompt
                        or str(current_goal.get("mode") or "story") != mode
                        or current_goal.get("source") != "ai"
                        or str(current_goal.get("generationId") or "") != generation_id):
                    return self._error("GOAL_PLAN_STALE", "世界目标已经变化，已忽略迟到的任务结果。")
                logic_blueprint = self._normalize_logic_blueprint(result)
                tasks = self._normalize_goal_plan_tasks(result, context, now)
                context["activeTasks"] = [
                    task for task in context.get("activeTasks") or []
                    if not isinstance(task, dict) or task.get("type") not in {"tutorial", "goal"}
                ] + tasks
                context["worldGoal"] = {
                    "prompt": prompt,
                    "mode": mode,
                    "source": "ai",
                    "status": "ready",
                    "generatedAt": now,
                    "generationError": "",
                    "generationId": generation_id,
                }
                context["goalTaskPlan"] = {
                    "schemaVersion": 2,
                    "generatedAt": now,
                    "taskCount": len(tasks),
                    "nodeTaskCount": sum(1 for task in tasks if task.get("phase") == "node-logic"),
                    "sceneTaskCount": sum(1 for task in tasks if task.get("phase") == "scene-polish"),
                    "logicBlueprint": logic_blueprint,
                }
                self._ensure_task_slots_locked(context, now)
                self._write_locked(project_path, context)
                return {"success": True, "status": "ok", "context": self._clone(context)}
        except urllib.error.HTTPError as exc:
            status = int(getattr(exc, "code", 0) or 0)
            message = "DeepSeek API Key 无效或无权限。" if status in {401, 403} else f"DeepSeek 请求失败（HTTP {status}）。"
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            message = "无法连接 DeepSeek，请稍后重试。"
        except Exception as exc:
            logger.warning("Cabbage world task generation failed: %s", type(exc).__name__)
            message = str(exc) or "世界任务生成失败。"
        failure_context = None
        with self._lock:
            context = self._read_locked(project_path)
            goal = context.get("worldGoal") if isinstance(context.get("worldGoal"), dict) else {}
            if (str(goal.get("prompt") or "") == prompt
                    and str(goal.get("mode") or "story") == mode
                    and goal.get("source") == "ai"
                    and str(goal.get("generationId") or "") == generation_id):
                goal.update({"status": "error", "generationError": message, "generatedAt": 0})
                context["worldGoal"] = goal
                self._ensure_task_slots_locked(context, self._now_ms())
                self._write_locked(project_path, context)
                failure_context = self._clone(context)
        failure = self._error("GOAL_PLAN_GENERATION_FAILED", message)
        if failure_context is not None:
            failure["context"] = failure_context
        return failure

    def _complete_goal_plan(self, task_id: str, future: Any) -> None:
        try:
            result = future.result()
        except Exception as exc:
            logger.warning("Cabbage world task generation callback failed: %s", type(exc).__name__)
            result = self._error("GOAL_PLAN_GENERATION_FAILED", "世界任务生成失败。")
        with self._lock:
            state = self._goal_plan_tasks.get(task_id)
            if state:
                state["status"] = "completed"
                state["result"] = result
                state["completedAt"] = time.time()

    def goal_plan_status(self, task_id: Any) -> dict[str, Any]:
        key = str(task_id or "")
        with self._lock:
            state = self._goal_plan_tasks.get(key)
            if not state:
                return self._error("GOAL_PLAN_TASK_NOT_FOUND", "没有找到这次世界任务生成请求。")
            response = {"success": True, "status": state["status"], "taskId": key}
            if state["status"] == "completed":
                response["result"] = self._clone(state.get("result") or {})
            return response

    def _prune_goal_plan_tasks_locked(self) -> None:
        if len(self._goal_plan_tasks) <= self.MAX_GOAL_PLAN_TASKS:
            return
        completed = sorted(
            (state for state in self._goal_plan_tasks.values() if state.get("status") == "completed"),
            key=lambda item: float(item.get("completedAt") or item.get("createdAt") or 0),
        )
        for state in completed[: max(0, len(self._goal_plan_tasks) - self.MAX_GOAL_PLAN_TASKS)]:
            self._goal_plan_tasks.pop(state["taskId"], None)

    @staticmethod
    def _event_categories(context: dict[str, Any]) -> set[str]:
        categories: set[str] = set()
        metrics = context.get("metrics") or {}
        if metrics.get("modelImports") or metrics.get("transformEdits"):
            categories.add("scene")
        if metrics.get("lightingEdits"):
            categories.add("lighting")
        if metrics.get("physicsEdits"):
            categories.add("physics")
        if metrics.get("nodeEdits") or metrics.get("nodeErrors") or metrics.get("nodeIssueFixes"):
            categories.add("node")
        if metrics.get("runSuccesses") or metrics.get("runFailures"):
            categories.add("runtime")
        return categories

    @classmethod
    def _can_update_score(cls, context: dict[str, Any], force: bool) -> tuple[bool, str]:
        metrics = context.get("metrics") or {}
        event_count = int(metrics.get("importantEventCount") or 0)
        last_count = int((context.get("profile") or {}).get("lastScoredEventCount") or 0)
        last_at = int((context.get("profile") or {}).get("updatedAt") or 0)
        high_value = any(int(metrics.get(key) or 0) > 0 for key in ("nodeEdits", "nodeIssueFixes", "runSuccesses", "runFailures"))
        recent_high_value = any(
            isinstance(event, dict)
            and int(event.get("timestamp") or 0) > last_at
            and event.get("type") in {"node_edited", "node_created", "node_connected", "block_added",
                                      "block_parameter_changed", "node_issue_fixed", "run_succeeded", "run_failed"}
            for event in context.get("recentOperationEvents") or []
        )
        if not force:
            if event_count < 6 and not high_value:
                return False, "insufficient_evidence"
            if len(cls._event_categories(context)) < 2 and not high_value:
                return False, "insufficient_categories"
            if last_at and cls._now_ms() - last_at < cls.SCORE_MIN_INTERVAL_SECONDS * 1000:
                return False, "score_update_cooldown"
            if last_at and event_count <= last_count:
                return False, "no_material_change"
            if last_at and event_count - last_count < 5 and not recent_high_value:
                return False, "no_material_change"
        return True, ""

    @classmethod
    def _score_evidence(cls, context: dict[str, Any]) -> dict[str, Any]:
        task_durations: list[float] = []
        issue_durations: list[float] = []
        completed_tutorials = 0
        for task in context.get("taskHistory") or []:
            if not isinstance(task, dict):
                continue
            created_at = int(task.get("createdAt") or 0)
            if task.get("type") == "tutorial" and int(task.get("completedAt") or 0) > created_at > 0:
                completed_tutorials += 1
                task_durations.append((int(task["completedAt"]) - created_at) / 1000.0)
            if task.get("type") == "node-issue" and int(task.get("resolvedAt") or 0) > 0:
                detected_at = int(task.get("firstDetectedAt") or created_at or 0)
                if detected_at > 0:
                    issue_durations.append((int(task["resolvedAt"]) - detected_at) / 1000.0)
        recent_events = [item for item in (context.get("recentOperationEvents") or []) if isinstance(item, dict)]
        recent_window = recent_events[-60:]
        successful_events = sum(1 for item in recent_window if item.get("success") is not False)
        failed_events = sum(1 for item in recent_window if item.get("success") is False)
        recent_runs = [item for item in recent_window if item.get("type") in {"run_succeeded", "run_failed"}]
        repeated_issue_count = sum(
            1 for entry in (context.get("issueMemory") or {}).values()
            if isinstance(entry, dict) and int(entry.get("occurrences") or 0) >= 2
        )
        metrics = context.get("metrics") or {}
        runs = int(metrics.get("runSuccesses") or 0) + int(metrics.get("runFailures") or 0)
        return {
            "completedTutorials": completed_tutorials,
            "medianTutorialSeconds": round(sorted(task_durations)[len(task_durations) // 2], 1) if task_durations else None,
            "medianIssueFixSeconds": round(sorted(issue_durations)[len(issue_durations) // 2], 1) if issue_durations else None,
            "runSuccessRate": round(int(metrics.get("runSuccesses") or 0) / runs, 3) if runs else None,
            "nodeIssueResolutionRate": round(
                int(metrics.get("nodeIssueFixes") or 0) / max(1, int(metrics.get("nodeErrors") or 0)), 3
            ) if int(metrics.get("nodeErrors") or 0) else None,
            "recentOperationSuccessRate": round(successful_events / max(1, successful_events + failed_events), 3),
            "recentRunSuccessRate": round(
                sum(1 for item in recent_runs if item.get("type") == "run_succeeded") / len(recent_runs), 3
            ) if recent_runs else None,
            "recentFailedOperations": failed_events,
            "repeatedIssueKinds": repeated_issue_count,
            "operationCategoryCount": len(cls._event_categories(context)),
        }

    @classmethod
    def _score_prompt(cls, context: dict[str, Any]) -> str:
        current_profile = context.get("profile") or {}
        evidence = {
            "metrics": context.get("metrics") or {},
            "scoreEvidence": cls._score_evidence(context),
            "tutorialTasks": [
                {
                    "title": task.get("title"),
                    "status": task.get("status"),
                    "completedAt": task.get("completedAt", 0),
                    "createdAt": task.get("createdAt", 0),
                }
                for task in (context.get("activeTasks") or []) + (context.get("taskHistory") or [])
                if isinstance(task, dict) and task.get("type") == "tutorial"
            ],
            "recentEvents": (context.get("recentOperationEvents") or [])[-60:],
            "issueMemory": context.get("issueMemory") or {},
            "profileHistory": (context.get("profileHistory") or [])[-8:],
            "currentScore": current_profile.get("score", 0),
        }
        return (
            "请根据 CoronaEngine 当前世界的操作证据，评估用户当前操作流畅度，给出 0 到 100 的连续分数。"
            "不判断用户是美术还是程序，不输出入门、熟悉或熟练等档位。"
            "分数必须可随后续表现上升或下降：近期任务完成更快、操作成功率提高、节点问题修复更快、运行更稳定时应提分；"
            "重复出现相同错误、运行失败增多、修复变慢或有效操作成功率下降时应降分。"
            "早期表现不能锁死后续分数，优先参考近期证据。"
            "只返回 JSON："
            '{"score":0,"reasonCodes":["short_reason_code"]}'
            "。score 必须是 0 到 100 的数字，reasonCodes 使用简短稳定代码。\n证据："
            + json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
        )

    def start_score_update(self, payload: Any = None) -> dict[str, Any]:
        force = bool(payload.get("force")) if isinstance(payload, dict) else False
        try:
            project_path = self._active_project_path()
            with self._lock:
                context = self._read_locked(project_path)
                allowed, reason = self._can_update_score(context, force)
                if not allowed:
                    return {"success": True, "status": "skipped", "reason": reason, "profile": self._clone(context["profile"])}
                for state in self._score_tasks.values():
                    if state.get("status") == "running" and state.get("projectPath") == str(project_path):
                        return {"success": True, "status": "pending", "taskId": state["taskId"]}
                task_id = f"cabbage_profile_{uuid.uuid4().hex}"
                state = {
                    "taskId": task_id,
                    "status": "running",
                    "projectPath": str(project_path),
                    "createdAt": time.time(),
                    "result": None,
                }
                self._score_tasks[task_id] = state
                future = self._executor.submit(self._compute_score, project_path, self._clone(context))
                future.add_done_callback(lambda done, key=task_id: self._complete_score_update(key, done))
                self._prune_score_tasks_locked()
                return {"success": True, "status": "pending", "taskId": task_id}
        except Exception as exc:
            logger.warning("Unable to start Cabbage assistance score update: %s", exc)
            return self._error("PROFILE_SCORE_FAILED", str(exc))

    def _compute_score(self, project_path: Path, context: dict[str, Any]) -> dict[str, Any]:
        settings = NodeGraphReviewService._resolve_settings()
        if not settings.api_key:
            return self._error("AI_NOT_CONFIGURED", "DeepSeek 未配置，暂时无法更新操作评分。")
        raw = NodeGraphReviewService._call_deepseek(settings, self._score_prompt(context))
        value = NodeGraphReviewService._parse_model_result(raw)
        raw_score = value.get("score", value.get("fluencyScore"))
        try:
            model_score = max(0, min(int(round(float(raw_score))), 100))
        except (TypeError, ValueError):
            raise ValueError("DeepSeek 返回的操作评分无效")
        reason_codes = [str(item)[:80] for item in (value.get("reasonCodes") or []) if str(item).strip()][:12]

        with self._lock:
            latest = self._read_locked(project_path)
            current = latest.get("profile") or {}
            has_previous_score = int(current.get("updatedAt") or 0) > 0
            current_score = max(0, min(int(current.get("score", current.get("fluencyScore", 0)) or 0), 100))
            accepted_score = (
                int(round(current_score * 0.35 + model_score * 0.65))
                if has_previous_score
                else model_score
            )
            now = self._now_ms()
            if has_previous_score:
                latest["profileHistory"].append({
                    "score": current_score,
                    "updatedAt": int(current.get("updatedAt") or 0),
                    "reasonCodes": list(current.get("reasonCodes") or [])[:12],
                })
                latest["profileHistory"] = latest["profileHistory"][-self.MAX_PROFILE_HISTORY :]
            profile = {
                "score": accepted_score,
                "source": "deepseek",
                "updatedAt": now,
                "reasonCodes": reason_codes,
                "lastScoredEventCount": int((latest.get("metrics") or {}).get("importantEventCount") or 0),
            }
            latest["profile"] = profile
            self._write_locked(project_path, latest)
        return {"success": True, "status": "ok", "profile": profile}

    def _complete_score_update(self, task_id: str, future: Any) -> None:
        try:
            result = future.result()
        except Exception as exc:
            logger.warning("Cabbage assistance score update failed: %s", exc)
            result = self._error("PROFILE_SCORE_FAILED", "操作评分更新暂时不可用。")
        with self._lock:
            state = self._score_tasks.get(task_id)
            if state:
                state["status"] = "completed"
                state["result"] = result
                state["completedAt"] = time.time()

    def score_update_status(self, task_id: Any) -> dict[str, Any]:
        key = str(task_id or "")
        with self._lock:
            state = self._score_tasks.get(key)
            if not state:
                return self._error("PROFILE_SCORE_TASK_NOT_FOUND", "没有找到操作评分更新任务。")
            response = {"success": True, "status": state["status"], "taskId": key}
            if state["status"] == "completed":
                response["result"] = self._clone(state.get("result") or {})
            return response

    def _prune_score_tasks_locked(self) -> None:
        if len(self._score_tasks) <= self.MAX_SCORE_TASKS:
            return
        completed = sorted(
            (state for state in self._score_tasks.values() if state.get("status") == "completed"),
            key=lambda item: float(item.get("completedAt") or item.get("createdAt") or 0),
        )
        for state in completed[: max(0, len(self._score_tasks) - self.MAX_SCORE_TASKS)]:
            self._score_tasks.pop(state["taskId"], None)

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)


_service: CabbageContextService | None = None


def get_cabbage_context_service() -> CabbageContextService:
    global _service
    if _service is None:
        _service = CabbageContextService()
    return _service
