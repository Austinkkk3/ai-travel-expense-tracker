"""
model_gateway.py
LLM inference layer using IBM watsonx.ai REST API directly.
Uses raw HTTP calls to avoid ibm-watsonx-ai SDK compatibility issues with Python 3.14.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

CLOUD_URL  = os.getenv("CLOUD_URL",  "https://us-south.ml.cloud.ibm.com")
API_KEY    = os.getenv("API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")
LLM_NAME   = os.getenv("LLM_NAME",  "ibm/granite-3-8b-instruct")

_iam_token_cache: dict = {}


def _get_iam_token() -> str:
    """Exchange IBM Cloud API key for a Bearer token (cached, auto-refreshes after 50 min)."""
    now = time.time()
    # IBM IAM tokens expire after 60 min — refresh after 50 min to be safe
    if _iam_token_cache.get("token") and now - _iam_token_cache.get("ts", 0) < 3000:
        return _iam_token_cache["token"]

    resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type":    "urn:ibm:params:oauth:grant-type:apikey",
            "apikey":        API_KEY,
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    _iam_token_cache["token"] = token
    _iam_token_cache["ts"]    = now
    return token


def invoke_llm(prompt: str) -> str:
    """
    Send a prompt to the watsonx.ai LLM and return the generated text.

    Args:
        prompt: The full prompt string to send to the model.

    Returns:
        The generated text response as a string.
    """
    token = _get_iam_token()

    url = f"{CLOUD_URL}/ml/v1/text/generation?version=2023-05-29"

    payload = {
        "model_id":   LLM_NAME,
        "project_id": PROJECT_ID,
        "input":      prompt,
        "parameters": {
            "max_new_tokens":     2048,
            "temperature":        0.0,
            "repetition_penalty": 1.05,
            "stop_sequences":     ["```"],
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()

    data = resp.json()
    return data["results"][0]["generated_text"]
