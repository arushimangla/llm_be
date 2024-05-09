import numpy as np
import pandas as pd
import torch
from datasets import load_dataset
import os

import nltk
import evaluate
from random import randrange

from transformers import AutoModelForSeq2SeqLM, TrainingArguments, pipeline, BitsAndBytesConfig, GemmaForCausalLM, GemmaTokenizer
import peft
from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from trl import SFTTrainer
from sentencepiece import SentencePieceProcessor
from huggingface_hub import login

class Gemma:
    def __init__(self, dataset_id, model_id):
      self.dataset_id = dataset_id
      self.model_id = model_id
      self.dataset = None
      self.tokenizer_id = None
      self.tokenizer = None
      self.model = None
      self.data_collator = None
      self.training_args = None
      self.training_args = None
      self.trainer = None
      self.summarizer = None
      self.max_source_length = None
      self.max_target_length = None

      self.initialize()
      self.sp_model = SentencePieceProcessor()
      self.sp_model.LoadFromFile(str(self.vocab_file))
      self.train_model()

    def initialize(self):

      login(token="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", #Adding token here since gemma is part of a gated repo
            add_to_git_credential=True)

      self.dataset = load_dataset(self.dataset_id, split = "train")

      self.tokenizer_id =  "philschmid/gemma-tokenizer-chatml"

      self.model = GemmaForCausalLM.from_pretrained(
          self.model_id,
          use_cache=False,
          use_flash_attention_2=False,
          device_map='auto',
          )

      self.tokenizer = GemmaTokenizer.from_pretrained(self.tokenizer_id)
      self.tokenizer.pad_token = self.tokenizer.eos_token
      self.tokenizer.padding_side = "right"

      # Model initialization
      self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id)

      # LoRA config based on QLoRA paper
      self.peft_config = LoraConfig(
                lora_alpha=8,
              lora_dropout=0.05,
              r=64,
              bias="none",
              task_type="CAUSAL_LM",
      )

    def train_model(self):
      try:
        # Additional setup for training
        repository_id = f"{self.model_id.split('/')[1]}-{self.dataset_id}"
        # Define training args
        training_args = TrainingArguments(
            output_dir="gemma-7b-dolly-chatml",
            num_train_epochs=3,
            per_device_train_batch_size=6,
            gradient_accumulation_steps=2,
            gradient_checkpointing=True,
            optim="paged_adamw_32bit",
            logging_steps=10,
            save_strategy="epoch",
            learning_rate=2e-4,
            bf16=False,
            fp16=False,
            tf32=False,
            max_grad_norm=0.3,
            warmup_ratio=0.03,
            lr_scheduler_type="constant",
            warmup_steps=0,
            save_total_limit=3,
            disable_tqdm=False,  # disable tqdm since with packing values are in correct
            )

        # Create Trainer instance
        trainer = SFTTrainer(
            model=self.model,
            train_dataset=self.dataset,
            peft_config= self.peft_config,
            tokenizer=self.tokenizer,
            dataset_text_field="text",
            max_seq_length=2048,
            args=training_args,
            packing=True,
            )

        # Start training
        trainer.train()

      except Exception as e:
        print(f"Error during training: {str(e)}")

obj = Gemma(dataset_id = 'philschmid/dolly-15k-oai-style', model_id = 'google/gemma-7b')
