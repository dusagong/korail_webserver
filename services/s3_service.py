"""
S3 이미지 업로드 서비스

리뷰 이미지를 AWS S3에 업로드하고 URL을 반환합니다.
"""
import boto3
import uuid
from typing import Optional
from fastapi import UploadFile
from botocore.exceptions import ClientError
from config import get_settings


class S3Service:
    """AWS S3 이미지 업로드 서비스"""

    def __init__(self):
        self.settings = get_settings()
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.aws_region,
        )
        self.bucket_name = self.settings.s3_bucket_name
        self.region = self.settings.aws_region

    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "reviews",
        custom_filename: Optional[str] = None
    ) -> str:
        """
        이미지를 S3에 업로드하고 URL 반환

        Args:
            file: FastAPI UploadFile 객체
            folder: S3 폴더 경로 (기본: reviews)
            custom_filename: 커스텀 파일명 (없으면 UUID 생성)

        Returns:
            S3 이미지 URL
        """
        # 파일 확장자 추출
        original_filename = file.filename or "image.jpg"
        extension = original_filename.rsplit(".", 1)[-1].lower()
        if extension not in ["jpg", "jpeg", "png", "gif", "webp"]:
            extension = "jpg"

        # 파일명 생성
        if custom_filename:
            filename = f"{custom_filename}.{extension}"
        else:
            filename = f"{uuid.uuid4()}.{extension}"

        # S3 키 (경로)
        s3_key = f"{folder}/{filename}"

        # Content-Type 설정
        content_type_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        content_type = content_type_map.get(extension, "image/jpeg")

        try:
            # 파일 읽기
            contents = await file.read()

            # S3 업로드
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=contents,
                ContentType=content_type,
            )

            # URL 생성
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            return url

        except ClientError as e:
            print(f"[S3] Upload error: {e}")
            raise Exception(f"S3 업로드 실패: {str(e)}")
        finally:
            # 파일 포인터 리셋
            await file.seek(0)

    async def upload_images(
        self,
        files: list[UploadFile],
        folder: str = "reviews"
    ) -> list[str]:
        """
        여러 이미지를 S3에 업로드

        Args:
            files: UploadFile 리스트
            folder: S3 폴더 경로

        Returns:
            S3 이미지 URL 리스트
        """
        urls = []
        for file in files:
            url = await self.upload_image(file, folder)
            urls.append(url)
        return urls

    def delete_image(self, image_url: str) -> bool:
        """
        S3에서 이미지 삭제

        Args:
            image_url: S3 이미지 URL

        Returns:
            삭제 성공 여부
        """
        try:
            # URL에서 S3 키 추출
            # https://bucket.s3.region.amazonaws.com/folder/filename.jpg
            s3_key = image_url.split(f"{self.bucket_name}.s3.{self.region}.amazonaws.com/")[-1]

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True

        except ClientError as e:
            print(f"[S3] Delete error: {e}")
            return False

    def delete_images(self, image_urls: list[str]) -> int:
        """
        여러 이미지 삭제

        Args:
            image_urls: S3 이미지 URL 리스트

        Returns:
            삭제된 이미지 수
        """
        deleted_count = 0
        for url in image_urls:
            if self.delete_image(url):
                deleted_count += 1
        return deleted_count


# 싱글톤 인스턴스
s3_service = S3Service()
