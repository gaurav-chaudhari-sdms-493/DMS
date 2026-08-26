from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.folder import Folder
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.chunk import Chunk
from app.models.metadata_item import MetadataItem
from app.models.audit_log import AuditLog
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.api_log import ApiLog
from app.models.sys_config import SysConfig
from app.models.page import DocumentPage
from app.models.fact import Fact
from app.models.fact_region import FactRegion
from app.models.template import Template
from app.models.entity_node import EntityNode
from app.models.entity_edge import EntityEdge
from app.models.record import Record
from app.models.record_amendment import RecordAmendment
from app.models.corpus_calibration import CorpusCalibration
from app.models.department import Department, DepartmentMember, DepartmentFolder
from app.models.retention_class import RetentionClass
from app.models.translation import Translation
from app.models.subscription import Subscription
from app.models.license import License
from app.models.table_shape_decision import TableShapeDecision
from app.models.ocr_archive import OCRArchive
from app.models.vlm_archive import VLMArchive
from app.models.field_trust_signal import FieldTrustSignal
from app.database import Base


