"""
Edge Node 模块 - 3S-EAD 架构边缘辅助节点
"""

import logging
import pickle
from typing import Optional, Dict, Any, List
import threading
import base64

logger = logging.getLogger(__name__)


class EdgeNode:
    """边缘辅助节点：持有 sk_edge，提供部分解密服务"""
    
    def __init__(self, split_context, host='0.0.0.0', port=5001):
        from ckks_fed.split_key_crypto import SplitKeyKGC
        self.split_context = split_context
        self.host = host
        self.port = port
        self.server_thread = None
        logger.info(f"EdgeNode initialized: {host}:{port}")
    
    def partial_decrypt(self, ciphertext_bytes: bytes) -> bytes:
        """本地部分解密"""
        import tenseal as ts
        ct = ts.ckks_vector_from(self.split_context.tenSeal_context, ciphertext_bytes)
        share = self.split_context.partial_decrypt(ct)
        return share.serialize()
    
    def start_server(self, debug=False):
        """启动 HTTP 服务（后台线程）"""
        try:
            from flask import Flask, request, jsonify
            app = Flask(__name__)
            
            @app.route('/health', methods=['GET'])
            def health():
                return jsonify({'status': 'ok', 'role': 'edge_node'})
            
            @app.route('/partial_decrypt', methods=['POST'])
            def handle_partial_decrypt():
                try:
                    ct_bytes = request.data
                    share_bytes = self.partial_decrypt(ct_bytes)
                    return share_bytes, 200, {'Content-Type': 'application/octet-stream'}
                except Exception as e:
                    logger.error(f"Partial decrypt failed: {e}")
                    return jsonify({'error': str(e)}), 500
            
            @app.route('/batch_partial_decrypt', methods=['POST'])
            def handle_batch():
                try:
                    data = request.get_json()
                    ct_list_b64 = data.get('ciphertexts', [])
                    shares_b64 = []
                    for ct_b64 in ct_list_b64:
                        ct_bytes = base64.b64decode(ct_b64)
                        share_bytes = self.partial_decrypt(ct_bytes)
                        shares_b64.append(base64.b64encode(share_bytes).decode())
                    return jsonify({'shares': shares_b64})
                except Exception as e:
                    logger.error(f"Batch partial decrypt failed: {e}")
                    return jsonify({'error': str(e)}), 500
            
            def run():
                app.run(host=self.host, port=self.port, debug=debug)
            
            self.server_thread = threading.Thread(target=run, daemon=True)
            self.server_thread.start()
            logger.info(f"EdgeNode HTTP server started at http://{self.host}:{self.port}")
        except ImportError:
            logger.warning("Flask not installed, HTTP server not available. Use partial_decrypt_local() instead.")


class EdgeNodeClient:
    """Edge Node 远程客户端"""
    
    def __init__(self, endpoint='http://localhost:5001'):
        self.endpoint = endpoint
        self.session = None
    
    def _get_session(self):
        if self.session is None:
            import requests
            self.session = requests.Session()
        return self.session
    
    def partial_decrypt(self, ciphertext_bytes: bytes):
        """请求 Edge Node 执行部分解密"""
        import requests
        from ckks_fed.split_key_crypto import PartialDecryptionShare
        
        response = requests.post(
            f"{self.endpoint}/partial_decrypt",
            data=ciphertext_bytes, timeout=30
        )
        response.raise_for_status()
        return PartialDecryptionShare.deserialize(response.content)
    
    def batch_partial_decrypt(self, ciphertext_bytes_list: List[bytes]) -> List:
        """批量部分解密"""
        import requests
        import base64
        from ckks_fed.split_key_crypto import PartialDecryptionShare
        
        ct_b64_list = [base64.b64encode(ct).decode() for ct in ciphertext_bytes_list]
        response = requests.post(
            f"{self.endpoint}/batch_partial_decrypt",
            json={'ciphertexts': ct_b64_list}, timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        shares = []
        for share_b64 in result['shares']:
            share_bytes = base64.b64decode(share_b64)
            shares.append(PartialDecryptionShare.deserialize(share_bytes))
        return shares
