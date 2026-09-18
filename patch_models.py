import re

with open('app.py', 'r') as f:
    content = f.read()

old_except = """    except requests.exceptions.RequestException as e:
        error_details = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_details += f" | Body: {e.response.text}"
        print(f"LLM request error: {error_details}")
        return {"error_type": "upstream", "error": f"LLM request failed: {error_details}"}"""

new_except = """    except requests.exceptions.RequestException as e:
        error_details = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_details += f" | Body: {e.response.text}"
            if e.response.status_code in [404, 400] and "model" in e.response.text.lower():
                try:
                    models_resp = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {api_key}"})
                    available = [m.get("id") for m in models_resp.json().get("data", [])]
                    error_details += f" | AVAILABLE MODELS ON YOUR TIER: {available}"
                except Exception as ex:
                    pass
        print(f"LLM request error: {error_details}")
        return {"error_type": "upstream", "error": f"LLM request failed: {error_details}"}"""

content = content.replace(old_except, new_except)

with open('app.py', 'w') as f:
    f.write(content)
