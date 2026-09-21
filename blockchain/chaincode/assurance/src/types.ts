/*
 * Hyperledger Fabric Smart Contract Types for Trustworthy CV Assurance
 * SIH-26228 / Air-Gapped Permissioned Ledger
 */

export enum AssuranceEventType {
    DATASET_REGISTERED = 'DATASET_REGISTERED',
    CONTRIBUTOR_REGISTERED = 'CONTRIBUTOR_REGISTERED',
    DATASET_ASSESSED = 'DATASET_ASSESSED',
    CONTRIBUTOR_RISK_RECORDED = 'CONTRIBUTOR_RISK_RECORDED',
    MODEL_REGISTERED = 'MODEL_REGISTERED',
    MODEL_VERIFIED = 'MODEL_VERIFIED',
    MODEL_TAMPER_DETECTED = 'MODEL_TAMPER_DETECTED',
    INFERENCE_RECORDED = 'INFERENCE_RECORDED',
    INFERENCE_VERIFIED = 'INFERENCE_VERIFIED',
    INFERENCE_TAMPER_DETECTED = 'INFERENCE_TAMPER_DETECTED',
    REPLAY_DETECTED = 'REPLAY_DETECTED',
    SHIFT_ASSESSMENT_RECORDED = 'SHIFT_ASSESSMENT_RECORDED',
    ASSURANCE_REPORT_RECORDED = 'ASSURANCE_REPORT_RECORDED',
    AUDIT_BATCH_ANCHORED = 'AUDIT_BATCH_ANCHORED',
    QUARANTINE_RECORDED = 'QUARANTINE_RECORDED'
}

export interface AssuranceEventRecord {
    docType: 'AssuranceEvent';
    eventId: string;
    eventType: AssuranceEventType;
    assetId: string;
    contributorId?: string;
    datasetVersion?: string;
    modelVersion?: string;
    imageHash?: string;
    modelHash?: string;
    manifestHash?: string;
    preprocessingHash?: string;
    inferenceHash?: string;
    predictionHash?: string;
    bindingHash?: string;
    reportHash?: string;
    auditRootHash?: string;
    merkleRoot?: string;
    batchSize?: number;
    severity?: string;
    disposition?: string;
    sequenceNumber?: number;
    timestampUtc: number;
    timestampIso: string;
    softwareVersion: string;
    previousEventId?: string;
    txId: string;
    blockNumber?: number;
    submittingMsp: string;
    submitterIdentity: string;
    metadata?: Record<string, any>;
}

export interface ContributorRecord {
    docType: 'Contributor';
    contributorId: string;
    orgMsp: string;
    registeredAtUtc: number;
    registeredAtIso: string;
    status: 'ACTIVE' | 'FLAGGED' | 'QUARANTINED';
    lastRiskScore?: number;
    lastRiskLevel?: string;
    totalSubmissions: number;
    totalFlaggedSubmissions: number;
    metadata?: Record<string, any>;
}

export interface ModelRecord {
    docType: 'Model';
    modelId: string;
    version: string;
    trustedDigestSha256: string;
    authorOrg: string;
    submittingMsp: string;
    registeredAtUtc: number;
    registeredAtIso: string;
    status: 'REGISTERED' | 'VERIFIED' | 'TAMPER_DETECTED' | 'QUARANTINED';
    architectureInfo?: Record<string, any>;
}

export interface DatasetRecord {
    docType: 'Dataset';
    datasetId: string;
    version: string;
    canonicalManifestHash: string;
    contributorId: string;
    submittingMsp: string;
    registeredAtUtc: number;
    registeredAtIso: string;
    sampleCount: number;
    status: 'REGISTERED' | 'ASSESSED' | 'QUARANTINED';
}

export interface VerificationResult {
    assetId: string;
    isVerified: boolean;
    registeredHash?: string;
    queriedHash: string;
    match: boolean;
    txId?: string;
    timestampIso?: string;
    submittingMsp?: string;
    details: string;
}
