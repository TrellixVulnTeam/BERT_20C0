# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from jieba import Tokenizer
# from jieba.posseg import POSTokenizer

import sentencepiece as spm
import tensorflow as tf
from sentencepiece import SentencePieceTrainer
import re

SPIECE_UNDERLINE = '▁'

class SPM(object):
	def __init__(self, config):
		self.config = config
		self.sp = spm.SentencePieceProcessor()

	def load_dict(self):
		self.dict = []
		try:
			with open(self.config.get("word_dict", None), "r") as frobj:
				for line in frobj:
					content = line.strip().split("\t")[0]
					self.dict.append(content)
				tf.logging.info("vocab path {} total vocab {}".format(
					self.config["word_dict"],len(self.dict)))
					
		except:
			raise ValueError("Not existed word piece dict")

	def add_extra_word(self, 
		extra_lst=["[PAD]", "[UNK]","[CLS]", "[SEP]", "[MASK]"]):
		extra_lst = extra_lst if extra_lst else self.config.get("extra_lst", [])
		if len(extra_lst) >= 1:
			for word in extra_lst:
				if word in self.dict:
					self.dict.remove(word)
			self.dict = extra_lst + self.dict
			with open("/data/xuht/tmp_vocab.txt", "w") as fwobj:
				for word in self.dict:
					fwobj.write(word+"\n")
		
	def build_word_id(self):
		self.word2id, self.id2word = {}, {}
		for index, word in enumerate(self.dict):
			self.word2id[word] = index
			self.id2word[index] = word
		
	def load_model(self):
		try:
			self.sp.Load(self.config.get("word_piece_model", None))
		except:
			raise ValueError('Not found word piece model')

	def train_model(self, train_config=None):
		'''
		https://github.com/google/sentencepiece/blob/master/python/sentencepiece_python_module_example.ipynb
		see from this tutorial for sentence piece training
		'''
		config = train_config if train_config else self.config
		param = ""
		param += "--input={} ".format(config["corpus"])
		param += "--model_prefix={} ".format(config["model_prefix"])
		param += "--vocab_size={} ".format(config["vocab_size"])
		param += "--model_type={} ".format(config.get("model_type", "unigram"))
		param += "--character_coverage={} ".format(config.get("character_coverage", 0.995))
		param += "--mining_sentence_size={} ".format(config.get("mining_sentence_size", 5000000))
		param += "--input_sentence_size={} ".format(config.get("input_sentence_size", 5000000))
		param += "--max_sentencepiece_length={} ".format(config.get("max_sentencepiece_length", 5))
		try:
			SentencePieceTrainer.Train(param)
			self.sp.Load(config["model_prefix"]+".model")
		except:
			raise ValueError(" training word piece model failed ")

	def tokenize(self, text):
		tokenized_text = self.encode_pieces(text)
		output = []
		for word in tokenized_text:
			tmp_word = word.replace(SPIECE_UNDERLINE, '')
			if len(tmp_word) >= 1:
				output.append(tmp_word)
		return output

	def encode_pieces(self, text, return_unicode=True, sample=False):
		# return_unicode is used only for py2

		# note(zhiliny): in some systems, sentencepiece only accepts str for py2
		if six.PY2 and isinstance(text, unicode):
			text = text.encode('utf-8')

		if not sample:
			pieces = self.sp.EncodeAsPieces(text)
		else:
			pieces = self.sp.SampleEncodeAsPieces(text, 64, 0.1)
		new_pieces = []
		for piece in pieces:
			if len(piece) > 1 and piece[-1] == ',' and piece[-2].isdigit():
				cur_pieces = self.sp.EncodeAsPieces(
					piece[:-1].replace(SPIECE_UNDERLINE, ''))
				if piece[0] != SPIECE_UNDERLINE and cur_pieces[0][0] == SPIECE_UNDERLINE:
					if len(cur_pieces[0]) == 1:
						cur_pieces = cur_pieces[1:]
					else:
						cur_pieces[0] = cur_pieces[0][1:]
				cur_pieces.append(piece[-1])
				new_pieces.extend(cur_pieces)
			else:
				new_pieces.append(piece)

		# note(zhiliny): convert back to unicode for py2
		if six.PY2 and return_unicode:
			ret_pieces = []
			for piece in new_pieces:
				if isinstance(piece, str):
					piece = piece.decode('utf-8')
				ret_pieces.append(piece)
				new_pieces = ret_pieces

		return new_pieces

	def convert_tokens_to_ids(self, text, unk="[UNK]"):
		try:
			tokenized_text = self.tokenize(text)
		except:
			tokenized_text = text
		token_id_lst = [self.word2id.get(word, self.word2id[unk]) for word in tokenized_text]
		return token_id_lst

	def padding(self, token_id_lst, max_length, zero_padding=0):
		return token_id_lst + [zero_padding] * (max_length - len(token_id_lst))

class Jieba(object):
	def __init__(self, config):
		self.config = config
		self.dt = POSTokenizer()

	def load_dict(self):
		self.dict = []
		try:
			with open(self.config.get("word_dict", None), "r") as frobj:
				for line in frobj:
					content = line.strip().split("\t")[0]
					self.dict.append(content)
		except:
			raise ValueError("Not existed word piece dict")

	def load_model(self):
		for word in self.dict:
			self.dt.add_word(word)

	def build_word_id(self):
		self.word2id, self.id2word = {}, {}
		for index, word in enumerate(self.dict):
			self.word2id[word] = index
			self.id2word[index] = word

	def add_extra_word(self, 
			extra_lst=["[PAD]", "[UNK]","[CLS]", "[SEP]", "[MASK]"]):
		extra_lst = extra_lst if extra_lst else self.config.get("extra_lst", [])
		if len(extra_lst) >= 1:
			for word in extra_lst:
				if word in self.dict:
					self.dict.remove(word)
			self.dict = extra_lst + self.dict

	def train_model(self, train_config=None):
		config = train_config if train_config else self.config
		self.dict = []
		try:
			with open(config.get("word_dict", None)) as frobj:
				for line in frobj:
					content = line.strip().split("\t")[0]
					self.dict.append(content)
		except:
			raise ValueError(" not existed word dict")

	def tokenize(self, text):
		tokenized_text = self.dt.lcut(text)
		return [list(word)[0] for word in tokenized_text]

	def convert_tokens_to_ids(self, text, unk="[UNK]"):
		tokenized_text = self.tokenize(text)
		token_id_lst = [self.word2id.get(word, self.word2id[unk]) for word in tokenized_text]
		return token_id_lst

class Jieba_CHAR(object):
	def __init__(self, config):
		print("----------using naive cut tool---------")
		self.config = config
		self.dt = POSTokenizer()

	def load_vocab(self, vocab_lst=None):
		try:
			self.word2id = {}
			for index, word in enumerate(vocab_lst):
				self.dt.add_word(word, 1e5)
				self.word2id[word] = index
			print("==total vocab==", len(self.word2id))
		except:
			print("==not included word list==")
		
	def tokenize(self, text):
		out = []
		char_pattern = re.compile(u"[\u4e00-\u9fa5]+")
		word_list = list(self.dt.lcut("".join(text.split())))
		for word in word_list:
			word = list(word)
			char_cn = char_pattern.findall(word[0])
			if len(char_cn) >= 1:
				for item in word[0]:
					if len(item) >= 1:
						out.append(item)
			else:
				if len(word[0]) >= 1:
					out.append(word[0])
		return out

	def convert_tokens_to_ids(self, token_lst, max_length):
		token_id_lst = [self.word2id["<pad>"] for _ in range(max_length)]
		for index, word in enumerate(token_lst[0:max_length]):
			if word in self.word2id:
				token_id_lst[index] = self.word2id[word]
			else:
				token_id_lst[index] = self.word2id["<unk>"]
		return token_id_lst

	def covert_tokens_to_char_ids(self, token_lst, max_length, char_len=5):
		char_id_lst = [[self.word2id["<pad>"] for _ in range(char_len)] for _ in range(max_length)]
		for index, word in enumerate(token_lst[0:max_length]):
			for char_index, char in enumerate(word[0:char_len]):
				if char in self.word2id:
					char_id_lst[index][char_index] = self.word2id[char]
				else:
					char_id_lst[index][char_index] = self.word2id["<unk>"]
		return char_id_lst


"""Tokenization classes."""

import collections
import unicodedata
import six
import tensorflow as tf

def convert_to_unicode(text):
	"""Converts `text` to Unicode (if it's not already), assuming utf-8 input."""
	if six.PY3:
		if isinstance(text, str):
			return text
		elif isinstance(text, bytes):
			return text.decode("utf-8", "ignore")
		else:
			raise ValueError("Unsupported string type: %s" % (type(text)))
	elif six.PY2:
		if isinstance(text, str):
			return text.decode("utf-8", "ignore")
		elif isinstance(text, unicode):
			return text
		else:
			raise ValueError("Unsupported string type: %s" % (type(text)))
	else:
		raise ValueError("Not running on Python2 or Python 3?")


def printable_text(text):
	"""Returns text encoded in a way suitable for print or `tf.logging`."""

	# These functions want `str` for both Python2 and Python3, but in one case
	# it's a Unicode string and in the other it's a byte string.
	if six.PY3:
		if isinstance(text, str):
			return text
		elif isinstance(text, bytes):
			return text.decode("utf-8", "ignore")
		else:
			raise ValueError("Unsupported string type: %s" % (type(text)))
	elif six.PY2:
		if isinstance(text, str):
			return text
		elif isinstance(text, unicode):
			return text.encode("utf-8")
		else:
			raise ValueError("Unsupported string type: %s" % (type(text)))
	else:
		raise ValueError("Not running on Python2 or Python 3?")


def load_vocab(vocab_file):
	"""Loads a vocabulary file into a dictionary."""
	vocab = collections.OrderedDict()
	index = 0
	with tf.gfile.GFile(vocab_file, "r") as reader:
		while True:
			token = convert_to_unicode(reader.readline())
			if not token:
				break
			token = token.strip()
			vocab[token] = index
			index += 1
	return vocab


def convert_by_vocab(vocab, items):
	"""Converts a sequence of [tokens|ids] using the vocab."""
	output = []
	for item in items:
		if item.startswith("##") and item.split("##")[-1] in vocab:
			if len(item.split("##")[-1]) == 1:
				cp = ord(item.split("##")[-1])
				if _is_chinese_char(cp):
					output.append(vocab.get(item.split("##")[-1], vocab["[UNK]"]))
				else:
					output.append(vocab.get(item, vocab["[UNK]"]))
			else:
				output.append(vocab.get(item, vocab["[UNK]"]))
		else:
			output.append(vocab.get(item, vocab["[UNK]"]))
	return output


def convert_tokens_to_ids(vocab, tokens):
	return convert_by_vocab(vocab, tokens)


def convert_ids_to_tokens(inv_vocab, ids):
	def convert_by_vocab(vocab, items):
		"""Converts a sequence of [tokens|ids] using the vocab."""
		output = []
		for item in items:
			output.append(vocab[item])
		return output
	return convert_by_vocab(inv_vocab, ids)


def whitespace_tokenize(text):
	"""Runs basic whitespace cleaning and splitting on a piece of text."""
	text = text.strip()
	if not text:
		return []
	tokens = text.split()
	return tokens


class FullTokenizer(object):
	"""Runs end-to-end tokenziation."""
	def __init__(self, vocab_file, do_lower_case=True, do_whole_word_mask=False):
		self.vocab = load_vocab(vocab_file)
		self.inv_vocab = {v: k for k, v in self.vocab.items()}
		self.basic_tokenizer = BasicTokenizer(do_lower_case=do_lower_case, 
												do_whole_word_mask=do_whole_word_mask)
		self.wordpiece_tokenizer = WordpieceTokenizer(vocab=self.vocab)

	def tokenize(self, text):
		split_tokens = []
		for token in self.basic_tokenizer.tokenize(text):
			for sub_token in self.wordpiece_tokenizer.tokenize(token):
				split_tokens.append(sub_token)

		return split_tokens

	def convert_tokens_to_ids(self, tokens, max_length=None):
		return convert_tokens_to_ids(self.vocab, tokens)

	def convert_ids_to_tokens(self, ids):
		return convert_ids_to_tokens(self.inv_vocab, ids)

	def covert_tokens_to_char_ids(self, tokens, max_length=None, char_len=5):
		pass

	def padding(self, token_id_lst, max_length, zero_padding=0):
		return token_id_lst + [zero_padding] * (max_length - len(token_id_lst))
		
	def is_start_id(self, token_id):
		token = self.inv_vocab[token_id]
		return not token.startswith("##")

	def is_start_token(self, token):
		return not token.startswith("##")

	def is_func_id(self, token_id):
		token = self.inv_vocab[token_id]
		return self.is_func_token(token)

	def is_func_token(self, token):
		return token != "[UNK]" and token.startswith("<") and token.endswith(">")

class BasicTokenizer(object):
	"""Runs basic tokenization (punctuation splitting, lower casing, etc.)."""

	def __init__(self, do_lower_case=True, do_whole_word_mask=False):
		"""Constructs a BasicTokenizer.
		Args:
			do_lower_case: Whether to lower case the input.
		"""
		self.do_lower_case = do_lower_case
		self.do_whole_word_mask = do_whole_word_mask

	def tokenize(self, text):
		"""Tokenizes a piece of text."""
		text = convert_to_unicode(text)
		text = self._clean_text(text)

		# This was added on November 1st, 2018 for the multilingual and Chinese
		# models. This is also applied to the English models now, but it doesn't
		# matter since the English models were not trained on any Chinese data
		# and generally don't have any Chinese data in them (there are Chinese
		# characters in the vocabulary because Wikipedia does have some Chinese
		# words in the English Wikipedia.).
		if not self.do_whole_word_mask:
			text = self._tokenize_chinese_chars(text)

		orig_tokens = whitespace_tokenize(text)
		split_tokens = []
		for token in orig_tokens:
			if self.do_lower_case:
				token = token.lower()
				token = self._run_strip_accents(token)
			split_tokens.extend(self._run_split_on_punc(token))

		output_tokens = whitespace_tokenize(" ".join(split_tokens))
		return output_tokens

	def _run_strip_accents(self, text):
		"""Strips accents from a piece of text."""
		text = unicodedata.normalize("NFD", text)
		output = []
		for char in text:
			cat = unicodedata.category(char)
			if cat == "Mn":
				continue
			output.append(char)
		return "".join(output)

	def _run_split_on_punc(self, text):
		"""Splits punctuation on a piece of text."""
		chars = list(text)
		i = 0
		start_new_word = True
		output = []
		while i < len(chars):
			char = chars[i]
			if _is_punctuation(char):
				output.append([char])
				start_new_word = True
			else:
				if start_new_word:
					output.append([])
				start_new_word = False
				output[-1].append(char)
			i += 1

		return ["".join(x) for x in output]

	def _tokenize_chinese_chars(self, text):
		"""Adds whitespace around any CJK character."""
		output = []
		for char in text:
			cp = ord(char)
			if self._is_chinese_char(cp):
				output.append(" ")
				output.append(char)
				output.append(" ")
			else:
				output.append(char)
		return "".join(output)

	def _is_chinese_char(self, cp):
		"""Checks whether CP is the codepoint of a CJK character."""
		# This defines a "chinese character" as anything in the CJK Unicode block:
		#   https://en.wikipedia.org/wiki/CJK_Unified_Ideographs_(Unicode_block)
		#
		# Note that the CJK Unicode block is NOT all Japanese and Korean characters,
		# despite its name. The modern Korean Hangul alphabet is a different block,
		# as is Japanese Hiragana and Katakana. Those alphabets are used to write
		# space-separated words, so they are not treated specially and handled
		# like the all of the other languages.
		if ((cp >= 0x4E00 and cp <= 0x9FFF) or  #
			(cp >= 0x3400 and cp <= 0x4DBF) or  #
			(cp >= 0x20000 and cp <= 0x2A6DF) or  #
			(cp >= 0x2A700 and cp <= 0x2B73F) or  #
			(cp >= 0x2B740 and cp <= 0x2B81F) or  #
			(cp >= 0x2B820 and cp <= 0x2CEAF) or
			(cp >= 0xF900 and cp <= 0xFAFF) or  #
			(cp >= 0x2F800 and cp <= 0x2FA1F)):  #
			return True

		return False

	def _clean_text(self, text):
		"""Performs invalid character removal and whitespace cleanup on text."""
		output = []
		for char in text:
			cp = ord(char)
			if cp == 0 or cp == 0xfffd or _is_control(char):
				continue
			if _is_whitespace(char):
				output.append(" ")
			else:
				output.append(char)
		return "".join(output)


class WordpieceTokenizer(object):
	"""Runs WordPiece tokenziation."""

	def __init__(self, vocab, unk_token="[UNK]", max_input_chars_per_word=200):
		self.vocab = vocab
		self.unk_token = unk_token
		self.max_input_chars_per_word = max_input_chars_per_word

	def tokenize(self, text):
		"""Tokenizes a piece of text into its word pieces.
		This uses a greedy longest-match-first algorithm to perform tokenization
		using the given vocabulary.
		For example:
			input = "unaffable"
			output = ["un", "##aff", "##able"]
		Args:
			text: A single token or whitespace separated tokens. This should have
			already been passed through `BasicTokenizer.
		Returns:
			A list of wordpiece tokens.
		"""

		text = convert_to_unicode(text)

		output_tokens = []
		for token in whitespace_tokenize(text):
			chars = list(token)
			if len(chars) > self.max_input_chars_per_word:
				output_tokens.append(self.unk_token)
				continue

			is_bad = False
			start = 0
			sub_tokens = []
			while start < len(chars):
				end = len(chars)
				cur_substr = None
				while start < end:
					substr = "".join(chars[start:end])
					if start > 0:
						substr = "##" + substr
					if substr in self.vocab:
						cur_substr = substr
						break
					end -= 1
				if cur_substr is None:
					is_bad = True
					break
				sub_tokens.append(cur_substr)
				start = end

			if is_bad:
				output_tokens.append(self.unk_token)
			else:
				output_tokens.extend(sub_tokens)
		return output_tokens

def _is_chinese_char(cp):
	"""Checks whether CP is the codepoint of a CJK character."""
	# This defines a "chinese character" as anything in the CJK Unicode block:
	#   https://en.wikipedia.org/wiki/CJK_Unified_Ideographs_(Unicode_block)
	#
	# Note that the CJK Unicode block is NOT all Japanese and Korean characters,
	# despite its name. The modern Korean Hangul alphabet is a different block,
	# as is Japanese Hiragana and Katakana. Those alphabets are used to write
	# space-separated words, so they are not treated specially and handled
	# like the all of the other languages.
	if ((cp >= 0x4E00 and cp <= 0x9FFF) or  #
		(cp >= 0x3400 and cp <= 0x4DBF) or  #
		(cp >= 0x20000 and cp <= 0x2A6DF) or  #
		(cp >= 0x2A700 and cp <= 0x2B73F) or  #
		(cp >= 0x2B740 and cp <= 0x2B81F) or  #
		(cp >= 0x2B820 and cp <= 0x2CEAF) or
		(cp >= 0xF900 and cp <= 0xFAFF) or  #
		(cp >= 0x2F800 and cp <= 0x2FA1F)):  #
		return True

	return False

def _is_whitespace(char):
	"""Checks whether `chars` is a whitespace character."""
	# \t, \n, and \r are technically contorl characters but we treat them
	# as whitespace since they are generally considered as such.
	if char == " " or char == "\t" or char == "\n" or char == "\r":
		return True
	cat = unicodedata.category(char)
	if cat == "Zs":
		return True
	return False


def _is_control(char):
	"""Checks whether `chars` is a control character."""
	# These are technically control characters but we count them as whitespace
	# characters.
	if char == "\t" or char == "\n" or char == "\r":
		return False
	cat = unicodedata.category(char)
	if cat.startswith("C"):
		return True
	return False


def _is_punctuation(char):
	"""Checks whether `chars` is a punctuation character."""
	cp = ord(char)
	# We treat all non-letter/number ASCII as punctuation.
	# Characters such as "^", "$", and "`" are not in the Unicode
	# Punctuation class but we treat them as punctuation anyways, for
	# consistency.
	if ((cp >= 33 and cp <= 47) or (cp >= 58 and cp <= 64) or
		(cp >= 91 and cp <= 96) or (cp >= 123 and cp <= 126)):
		return True
	cat = unicodedata.category(char)
	if cat.startswith("P"):
		return True
	return False
