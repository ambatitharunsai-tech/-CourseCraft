import re

with open('app.py', 'r') as f:
    content = f.read()

old_except = """    except requests.exceptions.RequestException as e:
        print(f"LLM request error: {e}")
        return {"error_type": "upstream", "error": "LLM request failed"}"""

new_except = """    except requests.exceptions.RequestException as e:
        error_details = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_details += f" | Body: {e.response.text}"
        print(f"LLM request error: {error_details}")
        return {"error_type": "upstream", "error": f"LLM request failed: {error_details}"}"""

content = content.replace(old_except, new_except)

with open('app.py', 'w') as f:
    f.write(content)

