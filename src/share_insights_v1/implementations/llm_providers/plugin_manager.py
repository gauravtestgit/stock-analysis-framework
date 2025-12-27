import os
import yaml
import importlib
from typing import Dict, Any, List, Optional, Type
from ...interfaces.llm_provider import ILLMProvider

class LLMPluginManager:
    """Plugin manager for LLM providers with configuration-driven loading"""
    
    def __init__(self, config_path: str = "src/share_insights_v1/config/llm_config.yaml"):
        self.config_path = config_path
        self.config = None
        self.registry = {}
        print(f"[PLUGIN_DEBUG] Initializing LLM Plugin Manager with config: {config_path}")
        
        try:
            self._load_config()
            self._register_plugins()
            print(f"[PLUGIN_DEBUG] Successfully registered {len(self.registry)} providers")
        except Exception as e:
            print(f"[PLUGIN_DEBUG] Plugin manager initialization failed: {e}")
            # Don't raise - allow fallback to legacy system
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            # Try relative to project root first
            config_paths = [
                self.config_path,
                os.path.join(os.path.dirname(__file__), "../../config", "llm_config.yaml"),
                os.path.join(os.path.dirname(__file__), "../../../..", self.config_path),
                os.path.join(os.getcwd(), self.config_path)
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        self.config = yaml.safe_load(f)
                    print(f"[PLUGIN_DEBUG] Loaded config from: {path}")
                    return
            
            raise FileNotFoundError(f"Config file not found in any of: {config_paths}")
            
        except Exception as e:
            print(f"[PLUGIN_DEBUG] Failed to load config: {e}")
            raise
    
    def _register_plugins(self):
        """Register all plugins from configuration"""
        if not self.config or 'llm_providers' not in self.config:
            raise ValueError("Invalid config: missing llm_providers section")
        
        for provider_config in self.config['llm_providers']:
            try:
                self._register_plugin(provider_config)
            except Exception as e:
                print(f"[PLUGIN_DEBUG] Failed to register {provider_config.get('name', 'unknown')}: {e}")
                # Continue with other providers
    
    def _register_plugin(self, provider_config: Dict[str, Any]):
        """Register a single plugin with validation"""
        # Validate required fields
        required_fields = ['name', 'class', 'module', 'default_model', 'api_key_env']
        for field in required_fields:
            if field not in provider_config:
                raise ValueError(f"Missing required field: {field}")
        
        name = provider_config['name']
        class_name = provider_config['class']
        module_path = provider_config['module']
        
        # Security: validate module path
        if not module_path.startswith('src.share_insights_v1.implementations.llm_providers'):
            raise SecurityError(f"Invalid module path: {module_path}")
        
        try:
            # Dynamic import
            module = importlib.import_module(module_path)
            provider_class = getattr(module, class_name)
            
            # Validate interface
            if not issubclass(provider_class, ILLMProvider):
                raise TypeError(f"{class_name} must implement ILLMProvider interface")
            
            # Register successfully
            self.registry[name] = {
                'class': provider_class,
                'config': provider_config
            }
            print(f"[PLUGIN_DEBUG] Registered provider: {name} ({class_name})")
            
        except Exception as e:
            print(f"[PLUGIN_DEBUG] Failed to load {name}: {e}")
            raise
    
    def create_provider(self, name: str, model: str = None) -> ILLMProvider:
        """Create provider instance via plugin system"""
        if name not in self.registry:
            raise ValueError(f"Provider '{name}' not registered. Available: {list(self.registry.keys())}")
        
        provider_info = self.registry[name]
        provider_class = provider_info['class']
        config = provider_info['config']
        
        # Use provided model or default
        model_name = model or config['default_model']
        
        print(f"[PLUGIN_DEBUG] Creating {name} provider with model: {model_name}")
        
        try:
            # Create provider instance
            provider = provider_class(model_name)
            print(f"[PLUGIN_DEBUG] Successfully created {name} provider")
            return provider
        except Exception as e:
            print(f"[PLUGIN_DEBUG] Failed to create {name} provider: {e}")
            raise
    
    def get_available_providers(self) -> List[str]:
        """Get list of registered provider names"""
        return list(self.registry.keys())
    
    def get_provider_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for specific provider"""
        if name in self.registry:
            return self.registry[name]['config']
        return None
    
    def get_available_models(self, provider_name: str) -> List[str]:
        """Get available models for a provider"""
        config = self.get_provider_config(provider_name)
        if config and 'models' in config:
            return [model['name'] for model in config['models']]
        return []
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get configuration formatted for UI consumption"""
        if not self.config:
            return {"providers": []}
        
        ui_providers = []
        for provider_config in self.config['llm_providers']:
            name = provider_config['name']
            
            # Check if provider is available (has required API key)
            available = self._check_provider_availability(name)
            
            ui_provider = {
                "name": name,
                "display_name": provider_config.get('display_name', name.title()),
                "description": provider_config.get('description', ''),
                "icon": provider_config.get('icon', '🔧'),
                "available": available,
                "default_model": provider_config.get('default_model'),
                "models": provider_config.get('models', [])
            }
            ui_providers.append(ui_provider)
        
        return {"providers": ui_providers}
    
    def _check_provider_availability(self, provider_name: str) -> bool:
        """Check if provider is available (has API key from config)"""
        config = self.get_provider_config(provider_name)
        if config and 'api_key_env' in config:
            env_var = config['api_key_env']
            return bool(os.getenv(env_var))
        print('Using fallback for llm api keys')
        # Fallback to hardcoded mapping for backward compatibility
        api_key_map = {
            'groq': 'GROQ_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'xai': 'XAI_API_KEY'
        }
        
        env_var = api_key_map.get(provider_name)
        if env_var:
            return bool(os.getenv(env_var))
        return False
    
    def is_available(self) -> bool:
        """Check if plugin manager is properly initialized"""
        return self.config is not None and len(self.registry) > 0

class SecurityError(Exception):
    """Raised when security validation fails"""
    pass