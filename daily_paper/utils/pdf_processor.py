"""
PDF Processing Utilities

封装PDF下载和文本提取功能
"""

import os
import time
import requests
from PyPDF2 import PdfReader
from pathlib import Path
import logging

MAX_PAPER_TEXT_LENGTH = 128000

def download_paper(url: str, paper_id: str, save_dir: str, retries: int = 3) -> bool:
    """
    下载并保存PDF论文
    
    Args:
        url: PDF下载链接
        paper_id: 论文ID
        save_dir: 保存目录
        retries: 重试次数
        
    Returns:
        是否下载成功
    """
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, f"{paper_id}.pdf")
    
    if os.path.exists(file_path):
        logging.info(f"文件已存在，跳过下载: {paper_id}")
        return True
    
    for attempt in range(retries):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 文件完整性校验
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    downloaded += len(chunk)
                    f.write(chunk)
                    
            # 简单校验文件完整性
            if total_size > 0 and downloaded != total_size:
                raise IOError("文件大小不匹配，可能下载不完整")
                
            logging.info(f"成功下载: {paper_id}")
            return True
            
        except Exception as e:
            if attempt < retries - 1:
                logging.warning(f"下载失败 {paper_id}，第{attempt+1}次重试...")
                time.sleep(2)
            else:
                logging.error(f"下载最终失败 {paper_id}: {str(e)}")
                try:
                    os.remove(file_path)
                except:
                    pass
                return False
    
    return False

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    提取PDF文本内容
    
    Args:
        pdf_path: PDF文件路径
        
    Returns:
        提取的文本内容
    """
    try:
        # 尝试使用PyPDF2解析
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            text = '\n'.join([page.extract_text() for page in reader.pages])
            # Unicode清理
            clean_text = text.encode('utf-8', 'ignore').decode('utf-8')
            
            # 文本长度限制
            if len(clean_text) > MAX_PAPER_TEXT_LENGTH:
                logging.warning(f"文本长度 {len(clean_text)} 字符，已截断")
                clean_text = clean_text[:MAX_PAPER_TEXT_LENGTH] + "[...截断...]"
            
            return clean_text
            
    except Exception as pdf_error:
        logging.error(f"PyPDF2解析失败: {pdf_path}")
        try:
            # 备选方案：使用pdfplumber
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = '\n'.join([page.extract_text() for page in pdf.pages])
                clean_text = text.encode('utf-8', 'ignore').decode('utf-8')
                
                if len(clean_text) > MAX_PAPER_TEXT_LENGTH:
                    logging.warning(f"文本长度 {len(clean_text)} 字符，已截断")
                    clean_text = clean_text[:MAX_PAPER_TEXT_LENGTH] + "[...截断...]"
                
                return clean_text
                
        except Exception as plumber_error:
            try:
                # 备选方案：使用PyMuPDF
                import fitz
                doc = fitz.open(pdf_path)
                text = '\n'.join([page.get_text() for page in doc])
                clean_text = text.encode('utf-8', 'ignore').decode('utf-8')
                
                if len(clean_text) > MAX_PAPER_TEXT_LENGTH:
                    logging.warning(f"文本长度 {len(clean_text)} 字符，已截断")
                    clean_text = clean_text[:MAX_PAPER_TEXT_LENGTH] + "[...截断...]"
                
                return clean_text
                
            except Exception as fitz_error:
                error_msg = (
                    f"PDF解析全部失败: {pdf_path}\n"
                    f"PyPDF2错误: {str(pdf_error)}\n"
                    f"pdfplumber错误: {str(plumber_error)}\n"
                    f"PyMuPDF错误: {str(fitz_error)}"
                )
                logging.error(error_msg)
                return ""

def process_paper_pdf(paper_url: str, paper_id: str, save_dir: str = "papers") -> str:
    """
    处理单篇论文PDF（下载+提取文本）
    
    Args:
        paper_url: 论文URL
        paper_id: 论文ID
        save_dir: 保存目录
        
    Returns:
        提取的文本内容
    """
    # 将abs URL转换为PDF URL
    pdf_url = paper_url.replace('abs', 'pdf')
    
    # 下载PDF
    if not download_paper(pdf_url, paper_id, save_dir):
        return ""
    
    # 提取文本
    pdf_path = os.path.join(save_dir, f"{paper_id}.pdf")
    return extract_text_from_pdf(pdf_path)

if __name__ == "__main__":
    # 测试函数
    test_url = "https://arxiv.org/abs/2108.09112"
    test_id = "2108.09112"
    
    text = process_paper_pdf(test_url, test_id)
    print(f"提取文本长度: {len(text)}")
    print(f"前100字符: {text[:100]}...") 