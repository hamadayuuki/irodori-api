import requests
import os
import aiohttp
import asyncio
from typing import List, Dict, Optional


class YahooShoppingClient:
    def __init__(self):
        self.app_id = os.getenv("YAHOO_APP_ID")
        self.pid = os.getenv("YAHOO_PID")
        self.sid = os.getenv("YAHOO_SID")
        self.base_url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
    
    def search_products(self, query: str, gender: str = "メンズ", limit: int = 10) -> List[Dict]:
        search_query = f"{query} {gender}"
        
        params = {
            "appid": self.app_id,
            "query": search_query,
            "results": limit,
            "sort": "-score",
            "in_stock": "true"
        }
        
        if self.pid:
            params["affiliate_type"] = "vc"
            if self.sid:
                params["affiliate_id"] = f"http://ck.jp.ap.valuecommerce.com/servlet/referral?sid={self.sid}&pid={self.pid}&vc_url="
            else:
                params["affiliate_id"] = f"http://ck.jp.ap.valuecommerce.com/servlet/referral?pid={self.pid}&vc_url="
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            products = []
            if data.get("hits"):
                for item in data["hits"]:
                    product = {
                        "name": item["name"],
                        "price": item["price"],
                        "url": item["url"],
                        "image_url": item.get("image", {}).get("medium", ""),
                        "store_name": item.get("seller", {}).get("name", "")
                    }
                    products.append(product)
            
            return products[:limit]
        
        except Exception as e:
            print(f"Yahoo Shopping API error: {e}")
            return []
    
    async def search_products_async(self, query: str, gender: str = "メンズ", limit: int = 10) -> List[Dict]:
        search_query = f"{query} {gender}"
        
        params = {
            "appid": self.app_id,
            "query": search_query,
            "results": limit,
            "sort": "-score",
            "in_stock": "true"
        }
        
        if self.pid:
            params["affiliate_type"] = "vc"
            if self.sid:
                params["affiliate_id"] = f"http://ck.jp.ap.valuecommerce.com/servlet/referral?sid={self.sid}&pid={self.pid}&vc_url="
            else:
                params["affiliate_id"] = f"http://ck.jp.ap.valuecommerce.com/servlet/referral?pid={self.pid}&vc_url="
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    data = await response.json()
                    
                    products = []
                    if data.get("hits"):
                        for item in data["hits"]:
                            product = {
                                "name": item["name"],
                                "price": item["price"],
                                "url": item["url"],
                                "image_url": item.get("image", {}).get("medium", ""),
                                "store_name": item.get("seller", {}).get("name", "")
                            }
                            products.append(product)
                    
                    return products[:limit]
        
        except asyncio.TimeoutError:
            print(f"Yahoo Shopping API timeout for query: {search_query}")
            return []
        except Exception as e:
            print(f"Yahoo Shopping API error: {e}")
            return []
    
    def extract_search_keywords(self, categorize_text: str) -> str:
        parts = categorize_text.split()
        if len(parts) >= 3:
            return " ".join(parts[:3])
        return categorize_text