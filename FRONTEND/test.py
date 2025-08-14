import requests

url = "https://api.nansat.tech/process_urls"
payload = {
    "image_a_url": "https://res.cloudinary.com/dscnf7iqd/image/upload/v1755124767/g7vdz3lhzxtz5gxa7rot.png",
    "image_b_url": "https://res.cloudinary.com/dscnf7iqd/image/upload/v1755124769/cjsykbyfhdp8fzrb7jkp.jpg"
}

resp = requests.post(url, json=payload)

print("Status:", resp.status_code)
print("Text:", resp.text)
