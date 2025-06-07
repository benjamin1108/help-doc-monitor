"""
配置文件加载工具

支持从主配置文件和厂商独立配置文件中加载配置信息
"""
import yaml
import os
from typing import Dict, Any


class ConfigLoader:
    """配置加载器类"""
    
    def __init__(self, main_config_file: str = "config.yaml"):
        """
        初始化配置加载器
        
        Args:
            main_config_file: 主配置文件路径
        """
        self.main_config_file = main_config_file
        self.main_config = self._load_yaml(main_config_file)
        
    def _load_yaml(self, file_path: str) -> Dict[str, Any]:
        """
        加载YAML文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            解析后的配置字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"配置文件不存在: {file_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"配置文件解析错误: {file_path}, 错误: {e}")
            return {}
    
    def get_vendor_config(self, vendor: str) -> Dict[str, Any]:
        """
        获取指定厂商的配置
        
        Args:
            vendor: 厂商名称 (aliyun, tencentcloud, huaweicloud, volcengine)
            
        Returns:
            厂商配置字典
        """
        vendors = self.main_config.get('vendors', {})
        vendor_info = vendors.get(vendor)
        
        if not vendor_info:
            print(f"未找到厂商配置: {vendor}")
            return {}
        
        config_file = vendor_info.get('config_file')
        if not config_file:
            print(f"厂商 {vendor} 未指定配置文件")
            return {}
        
        # 加载厂商配置文件
        vendor_config = self._load_yaml(config_file)
        
        # 合并默认设置
        default_settings = self.main_config.get('default_settings', {})
        self._merge_default_settings(vendor_config, default_settings)
        
        return vendor_config
    
    def _merge_default_settings(self, vendor_config: Dict[str, Any], default_settings: Dict[str, Any]):
        """
        将默认设置合并到厂商配置中（仅在厂商配置中不存在时）
        
        Args:
            vendor_config: 厂商配置
            default_settings: 默认设置
        """
        for key, value in default_settings.items():
            if key not in vendor_config:
                vendor_config[key] = value
            elif isinstance(value, dict) and isinstance(vendor_config.get(key), dict):
                # 递归合并字典
                for sub_key, sub_value in value.items():
                    if sub_key not in vendor_config[key]:
                        vendor_config[key][sub_key] = sub_value
    
    def get_available_vendors(self) -> Dict[str, str]:
        """
        获取可用的厂商列表
        
        Returns:
            厂商名称和描述的字典
        """
        vendors = self.main_config.get('vendors', {})
        return {vendor: info.get('description', info.get('name', vendor)) 
                for vendor, info in vendors.items()}
    
    def get_vendor_products(self, vendor: str) -> Dict[str, Any]:
        """
        获取指定厂商的产品配置
        
        Args:
            vendor: 厂商名称
            
        Returns:
            产品配置字典
        """
        vendor_config = self.get_vendor_config(vendor)
        return vendor_config.get('products', {})


# 创建全局配置加载器实例
config_loader = ConfigLoader() 