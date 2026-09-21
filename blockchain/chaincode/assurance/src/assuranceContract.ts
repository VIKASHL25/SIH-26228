/*
 * Hyperledger Fabric Smart Contract: AssuranceContract
 * Trustworthy Computer Vision Integrity Assurance & Forensic Evidence Ledger
 * SIH-26228 / Theme: Blockchain & Cybersecurity
 */

import { Context, Contract, Info, Returns, Transaction } from 'fabric-contract-api';
import {
    AssuranceEventRecord,
    AssuranceEventType,
    ContributorRecord,
    DatasetRecord,
    ModelRecord,
    VerificationResult
} from './types';

@Info({
    title: 'AssuranceContract',
    description: 'Smart contract for anchoring and verifying CV dataset, model, and inference integrity'
})
export class AssuranceContract extends Contract {

    constructor() {
        super('AssuranceContract');
    }

    /**
     * Initializes default consortium ledger state.
     */
    @Transaction()
    public async initLedger(ctx: Context): Promise<void> {
        const timestamp = this.getTxTimestamp(ctx);
        const initEvent: AssuranceEventRecord = {
            docType: 'AssuranceEvent',
            eventId: 'EVT-GENESIS-000',
            eventType: AssuranceEventType.AUDIT_BATCH_ANCHORED,
            assetId: 'GENESIS_ANCHOR',
            timestampUtc: timestamp,
            timestampIso: new Date(timestamp * 1000).toISOString(),
            softwareVersion: '1.0.0',
            txId: ctx.stub.getTxID(),
            submittingMsp: ctx.clientIdentity.getMSPID(),
            submitterIdentity: ctx.clientIdentity.getID(),
            metadata: {
                description: 'Genesis block anchor for SIH-26228 CV Integrity Assurance Ledger'
            }
        };

        await ctx.stub.putState(
            this.buildEventKey('EVT-GENESIS-000'),
            Buffer.from(JSON.stringify(initEvent))
        );
    }

    /**
     * Registers a verified contributor organization identity.
     */
    @Transaction()
    public async registerContributor(
        ctx: Context,
        contributorId: string,
        orgMsp: string,
        metadataJson: string
    ): Promise<string> {
        const clientMsp = ctx.clientIdentity.getMSPID();
        const timestamp = this.getTxTimestamp(ctx);
        const iso = new Date(timestamp * 1000).toISOString();

        const key = this.buildContributorKey(contributorId);
        const existing = await ctx.stub.getState(key);
        if (existing && existing.length > 0) {
            throw new Error(`Contributor with ID ${contributorId} is already registered on the ledger.`);
        }

        let metadata = {};
        try {
            metadata = JSON.parse(metadataJson || '{}');
        } catch {
            metadata = {};
        }

        const record: ContributorRecord = {
            docType: 'Contributor',
            contributorId,
            orgMsp: orgMsp || clientMsp,
            registeredAtUtc: timestamp,
            registeredAtIso: iso,
            status: 'ACTIVE',
            totalSubmissions: 0,
            totalFlaggedSubmissions: 0,
            metadata
        };

        await ctx.stub.putState(key, Buffer.from(JSON.stringify(record)));

        // Record on-chain assurance event
        const eventId = `EVT-CONTRIB-${contributorId}-${Math.floor(timestamp)}`;
        const event: AssuranceEventRecord = {
            docType: 'AssuranceEvent',
            eventId,
            eventType: AssuranceEventType.CONTRIBUTOR_REGISTERED,
            assetId: contributorId,
            contributorId,
            timestampUtc: timestamp,
            timestampIso: iso,
            softwareVersion: '1.0.0',
            txId: ctx.stub.getTxID(),
            submittingMsp: clientMsp,
            submitterIdentity: ctx.clientIdentity.getID(),
            metadata: { orgMsp: record.orgMsp }
        };

        await ctx.stub.putState(this.buildEventKey(eventId), Buffer.from(JSON.stringify(event)));
        return JSON.stringify(record);
    }

    /**
     * Registers a training dataset manifest SHA-256 fingerprint.
     */
    @Transaction()
    public async registerDataset(
        ctx: Context,
        datasetId: string,
        version: string,
        canonicalManifestHash: string,
        contributorId: string,
        sampleCountStr: string
    ): Promise<string> {
        const clientMsp = ctx.clientIdentity.getMSPID();
        const timestamp = this.getTxTimestamp(ctx);
        const iso = new Date(timestamp * 1000).toISOString();
        const sampleCount = parseInt(sampleCountStr, 10) || 0;

        const key = this.buildDatasetKey(datasetId, version);
        const record: DatasetRecord = {
            docType: 'Dataset',
            datasetId,
            version,
            canonicalManifestHash,
            contributorId,
            submittingMsp: clientMsp,
            registeredAtUtc: timestamp,
            registeredAtIso: iso,
            sampleCount,
            status: 'REGISTERED'
        };

        await ctx.stub.putState(key, Buffer.from(JSON.stringify(record)));

        // Anchor event
        const eventId = `EVT-DATASET-${datasetId}-${version}`;
        const event: AssuranceEventRecord = {
            docType: 'AssuranceEvent',
            eventId,
            eventType: AssuranceEventType.DATASET_REGISTERED,
            assetId: datasetId,
            contributorId,
            datasetVersion: version,
            manifestHash: canonicalManifestHash,
            timestampUtc: timestamp,
            timestampIso: iso,
            softwareVersion: '1.0.0',
            txId: ctx.stub.getTxID(),
            submittingMsp: clientMsp,
            submitterIdentity: ctx.clientIdentity.getID(),
            metadata: { sampleCount }
        };

        await ctx.stub.putState(this.buildEventKey(eventId), Buffer.from(JSON.stringify(event)));
        return JSON.stringify(record);
    }

    /**
     * Registers trusted reference model weights SHA-256 digest.
     */
    @Transaction()
    public async registerModel(
        ctx: Context,
        modelId: string,
        version: string,
        trustedDigestSha256: string,
        authorOrg: string
    ): Promise<string> {
        const clientMsp = ctx.clientIdentity.getMSPID();
        const timestamp = this.getTxTimestamp(ctx);
        const iso = new Date(timestamp * 1000).toISOString();

        const key = this.buildModelKey(modelId, version);
        const record: ModelRecord = {
            docType: 'Model',
            modelId,
            version,
            trustedDigestSha256,
            authorOrg: authorOrg || clientMsp,
            submittingMsp: clientMsp,
            registeredAtUtc: timestamp,
            registeredAtIso: iso,
            status: 'REGISTERED'
        };

        await ctx.stub.putState(key, Buffer.from(JSON.stringify(record)));

        // Anchor event
        const eventId = `EVT-MODEL-${modelId}-${version}`;
        const event: AssuranceEventRecord = {
            docType: 'AssuranceEvent',
            eventId,
            eventType: AssuranceEventType.MODEL_REGISTERED,
            assetId: modelId,
            modelVersion: version,
            modelHash: trustedDigestSha256,
            timestampUtc: timestamp,
            timestampIso: iso,
            softwareVersion: '1.0.0',
            txId: ctx.stub.getTxID(),
            submittingMsp: clientMsp,
            submitterIdentity: ctx.clientIdentity.getID(),
            metadata: { authorOrg }
        };

        await ctx.stub.putState(this.buildEventKey(eventId), Buffer.from(JSON.stringify(event)));
        return JSON.stringify(record);
    }

    /**
     * Records a generic cryptographic assurance event onto the immutable ledger.
     */
    @Transaction()
    public async recordAssuranceEvent(ctx: Context, eventJson: string): Promise<string> {
        const clientMsp = ctx.clientIdentity.getMSPID();
        const timestamp = this.getTxTimestamp(ctx);
        const iso = new Date(timestamp * 1000).toISOString();

        const payload = JSON.parse(eventJson);
        const eventId = payload.event_id || payload.eventId || `EVT-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;

        const event: AssuranceEventRecord = {
            docType: 'AssuranceEvent',
            eventId,
            eventType: (payload.event_type || payload.eventType) as AssuranceEventType,
            assetId: payload.asset_id || payload.assetId || 'UNKNOWN_ASSET',
            contributorId: payload.contributor_id || payload.contributorId,
            datasetVersion: payload.dataset_version || payload.datasetVersion,
            modelVersion: payload.model_version || payload.modelVersion,
            imageHash: payload.image_hash || payload.imageHash,
            modelHash: payload.model_hash || payload.modelHash,
            manifestHash: payload.manifest_hash || payload.manifestHash,
            preprocessingHash: payload.preprocessing_hash || payload.preprocessingHash,
            inferenceHash: payload.inference_hash || payload.inferenceHash,
            predictionHash: payload.prediction_hash || payload.predictionHash,
            bindingHash: payload.binding_hash || payload.bindingHash,
            reportHash: payload.report_hash || payload.reportHash,
            auditRootHash: payload.audit_root_hash || payload.auditRootHash,
            merkleRoot: payload.merkle_root || payload.merkleRoot,
            batchSize: payload.batch_size || payload.batchSize,
            severity: payload.severity,
            disposition: payload.disposition,
            sequenceNumber: payload.sequence_number || payload.sequenceNumber,
            timestampUtc: payload.timestamp_utc || timestamp,
            timestampIso: payload.timestamp_iso || iso,
            softwareVersion: payload.software_version || '1.0.0',
            previousEventId: payload.previous_event_id || payload.previousEventId,
            txId: ctx.stub.getTxID(),
            submittingMsp: clientMsp,
            submitterIdentity: ctx.clientIdentity.getID(),
            metadata: payload.metadata || {}
        };

        await ctx.stub.putState(this.buildEventKey(eventId), Buffer.from(JSON.stringify(event)));
        return JSON.stringify(event);
    }

    /**
     * Anchors a ProtectedInferenceRecord cryptographic binding hash onto the ledger.
     */
    @Transaction()
    public async recordInference(
        ctx: Context,
        recordId: string,
        imageHash: string,
        modelDigest: string,
        prepHash: string,
        bindingHash: string,
        nonce: string,
        seqStr: string,
        hmacRef: string
    ): Promise<string> {
        const clientMsp = ctx.clientIdentity.getMSPID();
        const timestamp = this.getTxTimestamp(ctx);
        const iso = new Date(timestamp * 1000).toISOString();
        const sequenceNumber = parseInt(seqStr, 10) || 0;

        const eventId = `EVT-INF-${recordId}`;
        const event: AssuranceEventRecord = {
            docType: 'AssuranceEvent',
            eventId,
            eventType: AssuranceEventType.INFERENCE_RECORDED,
            assetId: recordId,
            imageHash,
            modelHash: modelDigest,
            preprocessingHash: prepHash,
            bindingHash,
            sequenceNumber,
            timestampUtc: timestamp,
            timestampIso: iso,
            softwareVersion: '1.0.0',
            txId: ctx.stub.getTxID(),
            submittingMsp: clientMsp,
            submitterIdentity: ctx.clientIdentity.getID(),
            metadata: { nonce, hmacRef }
        };

        await ctx.stub.putState(this.buildEventKey(eventId), Buffer.from(JSON.stringify(event)));
        return JSON.stringify(event);
    }

    /**
     * Verifies whether an active runtime artifact hash matches the immutable ledger record.
     */
    @Transaction(false)
    @Returns('string')
    public async verifyArtifact(
        ctx: Context,
        assetId: string,
        expectedHash: string
    ): Promise<string> {
        // Search by direct event ID or asset history
        const eventKey = this.buildEventKey(`EVT-INF-${assetId}`);
        let eventBytes = await ctx.stub.getState(eventKey);

        if (!eventBytes || eventBytes.length === 0) {
            // Check generic event key
            eventBytes = await ctx.stub.getState(this.buildEventKey(assetId));
        }

        if (!eventBytes || eventBytes.length === 0) {
            const result: VerificationResult = {
                assetId,
                isVerified: false,
                queriedHash: expectedHash,
                match: false,
                details: `Asset ID ${assetId} has no corresponding anchor on the blockchain ledger.`
            };
            return JSON.stringify(result);
        }

        const event: AssuranceEventRecord = JSON.parse(eventBytes.toString());
        const ledgerHash = event.bindingHash || event.modelHash || event.manifestHash || event.reportHash;
        const isMatch = ledgerHash?.toLowerCase() === expectedHash.toLowerCase();

        const result: VerificationResult = {
            assetId,
            isVerified: isMatch,
            registeredHash: ledgerHash,
            queriedHash: expectedHash,
            match: isMatch,
            txId: event.txId,
            timestampIso: event.timestampIso,
            submittingMsp: event.submittingMsp,
            details: isMatch
                ? `Cryptographic match confirmed against ledger transaction ${event.txId}.`
                : `TAMPER DETECTED: Queried hash differs from original immutable blockchain anchor (${ledgerHash}).`
        };

        return JSON.stringify(result);
    }

    /**
     * Retrieves specific assurance event by ID.
     */
    @Transaction(false)
    @Returns('string')
    public async getEvent(ctx: Context, eventId: string): Promise<string> {
        const key = this.buildEventKey(eventId);
        const bytes = await ctx.stub.getState(key);
        if (!bytes || bytes.length === 0) {
            throw new Error(`Event with ID ${eventId} does not exist on the ledger.`);
        }
        return bytes.toString();
    }

    /**
     * Retrieves full immutable transaction history for an asset.
     */
    @Transaction(false)
    @Returns('string')
    public async getAssetHistory(ctx: Context, assetId: string): Promise<string> {
        const key = this.buildEventKey(`EVT-INF-${assetId}`);
        const iterator = await ctx.stub.getHistoryForKey(key);
        const history: any[] = [];

        let result = await iterator.next();
        while (!result.done) {
            if (result.value) {
                history.push({
                    txId: result.value.txId,
                    timestamp: result.value.timestamp,
                    isDelete: result.value.isDelete,
                    value: result.value.value ? JSON.parse(result.value.value.toString('utf8')) : null
                });
            }
            result = await iterator.next();
        }
        await iterator.close();
        return JSON.stringify(history);
    }

    // Helper key builders
    private buildEventKey(eventId: string): string {
        return `EVENT_${eventId}`;
    }

    private buildContributorKey(contributorId: string): string {
        return `CONTRIBUTOR_${contributorId}`;
    }

    private buildDatasetKey(datasetId: string, version: string): string {
        return `DATASET_${datasetId}_${version}`;
    }

    private buildModelKey(modelId: string, version: string): string {
        return `MODEL_${modelId}_${version}`;
    }

    private getTxTimestamp(ctx: Context): number {
        const txTimestamp = ctx.stub.getTxTimestamp();
        return txTimestamp.seconds.low + (txTimestamp.nanos / 1e9);
    }
}
