import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import traceback 
from pathlib import Path 

class ModelWrapper(torch.nn.Module):
    def __init__(self, model_to_wrap):
        super().__init__()
        self.model_to_wrap = model_to_wrap
        self.model_to_wrap.config.use_cache = False

    def forward(self, input_ids, attention_mask):
        outputs = self.model_to_wrap(
            input_ids=input_ids,
            attention_mask=attention_mask,
            past_key_values=None,  
            token_type_ids=None,   
            position_ids=None,
            head_mask=None,
            inputs_embeds=None,
            labels=None,
            use_cache=False,       
            output_attentions=False,
            output_hidden_states=False,
            return_dict=True       
        )
        return outputs.logits

def export_model_to_onnx(model_name_or_path, export_dir, onnx_model_filename="model.onnx"):
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    print(f"Loading model and tokenizer for '{model_name_or_path}'...")
    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
    tokenizer.save_pretrained(export_dir)
    print(f"Tokenizer saved to '{export_dir}'.")

    model = AutoModelForCausalLM.from_pretrained(model_name_or_path)
    model.eval() 

    wrapped_model = ModelWrapper(model)
    wrapped_model.eval() 

    dummy_input_ids = torch.randint(0, tokenizer.vocab_size, (1, 10), dtype=torch.long)
    dummy_attention_mask = torch.ones(1, 10, dtype=torch.long)
    
    dummy_inputs_for_wrapper = (dummy_input_ids, dummy_attention_mask)

    onnx_export_path = os.path.join(export_dir, onnx_model_filename)

    print(f"Exporting model to ONNX at '{onnx_export_path}'...")
    try:
        torch.onnx.export(
            wrapped_model,                     
            dummy_inputs_for_wrapper,          
            onnx_export_path,
            input_names=['input_ids', 'attention_mask'], 
            output_names=['logits'],                     
            dynamic_axes={
                'input_ids': {0: 'batch_size', 1: 'sequence_length'},
                'attention_mask': {0: 'batch_size', 1: 'sequence_length'},
                'logits': {0: 'batch_size', 1: 'sequence_length'}
            },
            opset_version=14, 
            do_constant_folding=True,
        )
        print("Model exported successfully to ONNX.")
    except Exception as e:
        print(f"Error during ONNX export: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    MODEL_TO_EXPORT = "model"  
    EXPORT_DIRECTORY = "onnx_model_output" 

    base_dir = Path(__file__).parent
    model_export_path_abs = base_dir / MODEL_TO_EXPORT
    export_directory_abs = base_dir / EXPORT_DIRECTORY
    
    print(f"Starting ONNX export for model: {model_export_path_abs}")
    print(f"Output directory: {export_directory_abs}")
    
    export_model_to_onnx(str(model_export_path_abs), str(export_directory_abs))
    
    print(f"\nReminder: You will use the EXPORT_DIRECTORY path (e.g., '{export_directory_abs}')")
    print("as the 'model_dir_path' in your Polycrypt application for probabilistic attacks.")
