"""
微信公众号发布服务
"""
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime


class WechatPublisher:
    """微信公众号文章发布服务"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        self.token_expires_at = None
    
    def _get_access_token(self) -> str:
        """获取微信 access_token"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        url = f"https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "access_token" in data:
            self.access_token = data["access_token"]
            # token 有效期7200秒，提前5分钟过期
            from datetime import timedelta
            self.token_expires_at = datetime.now() + timedelta(seconds=data.get("expires_in", 7200) - 300)
            return self.access_token
        else:
            raise Exception(f"获取access_token失败: {data}")
    
    def draft_article(
        self,
        title: str,
        content: str,
        author: Optional[str] = None,
        digest: Optional[str] = None,
        content_source_url: Optional[str] = None,
        thumb_media_id: Optional[str] = None,
        need_open_comment: bool = True,
        only_fans_can_comment: bool = False
    ) -> Dict[str, Any]:
        """
        创建图文消息素材（草稿）
        
        Args:
            title: 标题
            content: 图文消息的具体内容，支持HTML标签
            author: 作者
            digest: 图文消息的摘要，仅有单图文消息才有摘要，多图文此处为空
            content_source_url: 图文消息的原文地址
            thumb_media_id: 图文消息的封面图片素材id
            need_open_comment: 是否打开评论
            only_fans_can_comment: 是否只有粉丝可以评论
        """
        access_token = self._get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
        
        # 处理内容中的图片，上传到微信
        content = self._process_content_images(content, access_token)
        
        articles = [{
            "title": title,
            "content": content,
            "author": author or "",
            "digest": digest or "",
            "content_source_url": content_source_url or "",
            "thumb_media_id": thumb_media_id or "",
            "need_open_comment": 1 if need_open_comment else 0,
            "only_fans_can_comment": 1 if only_fans_can_comment else 0
        }]
        
        payload = {"articles": articles}
        
        response = requests.post(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        
        if "media_id" in result:
            return {
                "success": True,
                "media_id": result["media_id"],
                "created_at": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": result.get("errmsg", "未知错误"),
                "errcode": result.get("errcode")
            }
    
    def _process_content_images(self, content: str, access_token: str) -> str:
        """处理内容中的图片，上传到微信服务器"""
        import re
        
        # 查找所有图片URL
        img_pattern = r'<img[^\u003e]+src=["\']([^"\']+)["\']'
        urls = re.findall(img_pattern, content)
        
        for url in urls:
            if url.startswith('http'):
                try:
                    # 下载图片
                    img_response = requests.get(url, timeout=10)
                    if img_response.status_code == 200:
                        # 上传到微信
                        media_id = self._upload_image(img_response.content, access_token)
                        if media_id:
                            # 替换URL
                            content = content.replace(url, media_id)
                except Exception as e:
                    print(f"处理图片失败 {url}: {e}")
        
        return content
    
    def _upload_image(self, image_data: bytes, access_token: str) -> Optional[str]:
        """上传图片到微信服务器"""
        url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
        
        files = {'media': ('image.png', image_data, 'image/png')}
        response = requests.post(url, files=files)
        
        result = response.json()
        return result.get("url")
    
    def submit_for_publish(self, media_id: str) -> Dict[str, Any]:
        """
        将草稿提交发布
        
        Args:
            media_id: 草稿的media_id
        """
        access_token = self._get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={access_token}"
        
        payload = {"media_id": media_id}
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        result = response.json()
        
        if result.get("errcode") == 0:
            return {
                "success": True,
                "publish_id": result.get("publish_id"),
                "msg_data_id": result.get("msg_data_id")
            }
        else:
            return {
                "success": False,
                "error": result.get("errmsg", "发布失败"),
                "errcode": result.get("errcode")
            }
    
    def get_publish_status(self, publish_id: str) -> Dict[str, Any]:
        """查询发布状态"""
        access_token = self._get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/get?access_token={access_token}"
        
        payload = {"publish_id": publish_id}
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()
    
    def get_material_list(self, type: str = "news", offset: int = 0, count: int = 20) -> Dict[str, Any]:
        """获取素材列表"""
        access_token = self._get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={access_token}"
        
        payload = {
            "type": type,
            "offset": offset,
            "count": count
        }
        
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()


class WechatPublisherMock:
    """微信公众号发布模拟器（用于测试）"""
    
    def draft_article(self, **kwargs) -> Dict[str, Any]:
        """模拟创建草稿"""
        return {
            "success": True,
            "media_id": f"mock_media_{datetime.now().timestamp()}",
            "created_at": datetime.now().isoformat(),
            "note": "这是模拟数据，未实际发布到公众号"
        }
    
    def submit_for_publish(self, media_id: str) -> Dict[str, Any]:
        """模拟发布"""
        return {
            "success": True,
            "publish_id": f"mock_pub_{datetime.now().timestamp()}",
            "msg_data_id": f"mock_msg_{datetime.now().timestamp()}",
            "note": "这是模拟数据，未实际发布"
        }
