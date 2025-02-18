from abc import ABC, abstractmethod
import os
import logging
logger = logging.getLogger(__name__)


class EMBD(ABC):
    @abstractmethod
    def encode(self, conn, data):        
        pass

class SentenceEMBD(EMBD):
    def __init__(self, config: dict,):
        from sentence_transformers import SentenceTransformer,export_optimized_onnx_model
        self.model_dir = config.get("model_dir")
        self.device = config.get("device","cpu")
        # model_dir = "jinaai/jina-embeddings-v2-base-zh"
        if not os.path.exists(os.path.join(self.model_dir,"onnx","model_O3.onnx")):
            self.model = SentenceTransformer(
                self.model_dir,
                  backend="onnx", 
                  device=self.device,
                  model_kwargs={"file_name": "model.onnx"}
            )
            export_optimized_onnx_model(self.model, "O3", self.model_dir)
            logging.info(f"优化模型成功: {self.model_dir}")

        self.model = SentenceTransformer(
            self.model_dir,
            backend="onnx",
            model_kwargs={"file_name": "onnx/model_O3.onnx"},
            device=self.device,
        )
        logging.info(f"加载模型成功: {self.model_dir}")
        
    def encode(self, data):
        return self.model.encode(data)

def create_instance(class_name: str, *args, **kwargs) -> EMBD:
    """工厂方法创建embedding实例"""
    
    model_map = {
        "SentenceTransformer": SentenceEMBD,        
    }

    if cls := model_map.get(class_name):
        return cls(*args, **kwargs)
    raise ValueError(f"不支持的embedding类型: {class_name}")