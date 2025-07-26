"""Simple LoRA fine-tuning script for ORA models."""

from typing import Optional

from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from datasets import load_dataset
from peft import LoraConfig, get_peft_model


def finetune(
    model_name: str,
    dataset_name: str,
    output_dir: str,
    *,
    lora_r: int = 8,
    lora_alpha: int = 16,
    lora_dropout: float = 0.1,
    num_train_epochs: int = 1,
    learning_rate: float = 2e-4,
    batch_size: int = 1,
) -> None:
    """Fine-tune a model using LoRA.

    Parameters
    ----------
    model_name : str
        Base model identifier from HuggingFace Hub.
    dataset_name : str
        Dataset identifier.
    output_dir : str
        Where to save the fine-tuned model.
    lora_r : int, optional
        Rank of LoRA matrices.
    lora_alpha : int, optional
        Alpha scaling factor for LoRA.
    lora_dropout : float, optional
        Dropout probability for LoRA layers.
    num_train_epochs : int, optional
        Number of training epochs.
    learning_rate : float, optional
        Optimizer learning rate.
    batch_size : int, optional
        Training batch size per device.
    """

    model = AutoModelForCausalLM.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    dataset = load_dataset(dataset_name, split="train")

    lora_config = LoraConfig(r=lora_r, lora_alpha=lora_alpha, lora_dropout=lora_dropout)
    model = get_peft_model(model, lora_config)

    model.enable_input_require_grads()

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_train_epochs,
        learning_rate=learning_rate,
        per_device_train_batch_size=batch_size,
        logging_steps=10,
        save_steps=50,
    )

    def collate(examples):
        return tokenizer([ex["text"] for ex in examples], return_tensors="pt", padding=True, truncation=True)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=collate,
    )

    trainer.train()

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LoRA fine-tuning for ORA")
    parser.add_argument("model_name")
    parser.add_argument("dataset_name")
    parser.add_argument("output_dir")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.1)

    args = parser.parse_args()

    finetune(
        args.model_name,
        args.dataset_name,
        args.output_dir,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
    )
