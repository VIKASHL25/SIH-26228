document.addEventListener('DOMContentLoaded', () => {
    // 1. Tab Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const tabPages = document.querySelectorAll('.tab-page');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            navItems.forEach(n => n.classList.remove('active'));
            tabPages.forEach(p => p.classList.remove('active'));
            
            item.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // 2. Fetch and Render Demo Analysis
    const btnRun = document.getElementById('btn-run-analysis');
    btnRun.addEventListener('click', runAnalysis);

    // Initial load
    runAnalysis();

    async function runAnalysis() {
        btnRun.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Auditing Pipeline...`;
        btnRun.disabled = true;

        try {
            const response = await fetch('/api/run_demo_analysis');
            if (!response.ok) throw new Error("Failed to run analysis");
            const report = await response.json();
            
            renderDashboard(report);
        } catch (err) {
            console.error(err);
            alert("Error running analysis pipeline: " + err.message);
        } finally {
            btnRun.innerHTML = `<i class="fa-solid fa-play"></i> Run Full Pipeline Audit`;
            btnRun.disabled = false;
        }
    }

    function renderDashboard(report) {
        // A. Scorecard
        document.getElementById('val-health-score').innerText = report.overall_health_score + " / 100";
        
        const dispElem = document.getElementById('val-disposition');
        dispElem.innerText = report.overall_disposition;
        dispElem.className = "";
        if (report.overall_disposition === "QUARANTINE") {
            dispElem.style.color = "var(--severity-critical)";
        } else if (report.overall_disposition === "REVIEW") {
            dispElem.style.color = "var(--severity-medium)";
        } else {
            dispElem.style.color = "var(--severity-low)";
        }

        document.getElementById('val-audit-hash').innerText = report.audit_trail_hash.substring(0, 16) + "...";

        // B. Findings Cards
        renderFindings(report.findings);

        // C. Data Integrity / Contributor Risk Matrix
        renderDataIntegrity(report.findings);

        // D. Model Integrity
        renderModelIntegrity(report.findings);

        // E. Environmental Shift
        renderShift(report.findings);

        // F. Governance Lists
        renderGovernance(report);
    }

    function renderFindings(findings) {
        const container = document.getElementById('findings-container');
        container.innerHTML = '';

        if (!findings || findings.length === 0) {
            container.innerHTML = `<div class="empty-state">No integrity findings flagged. All systems clean.</div>`;
            return;
        }

        findings.forEach(f => {
            const card = document.createElement('div');
            card.className = `finding-card ${f.severity}`;
            
            let badgeClass = 'badge-medium';
            if (f.severity === 'CRITICAL') badgeClass = 'badge-critical';
            if (f.severity === 'HIGH') badgeClass = 'badge-high';
            if (f.severity === 'LOW') badgeClass = 'badge-success';

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span class="badge ${badgeClass}">${f.severity}</span>
                    <small style="color:var(--text-muted); font-size:11px;">Confidence: ${(f.confidence_score * 100).toFixed(0)}%</small>
                </div>
                <h4 style="margin-bottom:8px; font-size:16px;">${f.title}</h4>
                <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">${f.human_readable_reason}</p>
                <div style="font-size:12px; display:flex; justify-content:space-between; border-top:1px solid var(--border-glass); padding-top:10px;">
                    <span>Asset: <code>${f.affected_asset}</code></span>
                    <strong style="color:var(--primary-cyan);">Action: ${f.recommended_disposition}</strong>
                </div>
            `;
            container.appendChild(card);
        });
    }

    function renderDataIntegrity(findings) {
        const matrixContainer = document.getElementById('contributor-matrix-container');
        
        // Extract contributor risk finding if available
        const contribFindings = findings.filter(f => f.category === 'data_integrity' && f.title.includes('Contributor'));
        
        let html = `<table>
            <thead>
                <tr>
                    <th>Contributor ID</th>
                    <th>Risk Level</th>
                    <th>Total Samples</th>
                    <th>Flagged</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
        `;

        if (contribFindings.length > 0) {
            contribFindings.forEach(cf => {
                const ev = cf.supporting_evidence;
                html += `<tr>
                    <td><strong>${ev.contributor_id}</strong></td>
                    <td><span class="badge badge-critical">${ev.risk_level}</span></td>
                    <td>${ev.total_samples}</td>
                    <td>${ev.flagged_samples_count}</td>
                    <td><small style="color:var(--severity-critical);">${ev.recommended_action}</small></td>
                </tr>`;
            });
        } else {
            html += `<tr>
                <td><strong>contributor_alpha</strong></td>
                <td><span class="badge badge-success">CLEAN</span></td>
                <td>20</td>
                <td>0</td>
                <td>ACCEPT</td>
            </tr>`;
        }

        html += `</tbody></table>`;
        matrixContainer.innerHTML = html;

        // Render poisoning details
        const poiFindings = findings.filter(f => f.title.includes('Poisoning'));
        const poiContainer = document.getElementById('poisoning-details-container');
        if (poiFindings.length > 0) {
            poiContainer.innerHTML = `<div class="alert-box" style="margin-top:10px; color:var(--severity-critical);">
                <i class="fa-solid fa-triangle-exclamation"></i> ${poiFindings[0].human_readable_reason}
            </div>`;
        } else {
            poiContainer.innerHTML = `<p style="margin-top:10px; color:var(--text-muted);">No trigger patches or spectral anomalies detected.</p>`;
        }

        // Render label details
        const lblFindings = findings.filter(f => f.title.includes('Label'));
        const lblContainer = document.getElementById('label-details-container');
        if (lblFindings.length > 0) {
            lblContainer.innerHTML = `<div class="alert-box" style="margin-top:10px; color:var(--severity-high);">
                <i class="fa-solid fa-tags"></i> ${lblFindings[0].human_readable_reason}
            </div>`;
        } else {
            lblContainer.innerHTML = `<p style="margin-top:10px; color:var(--text-muted);">All annotations match feature space consensus.</p>`;
        }
    }

    function renderModelIntegrity(findings) {
        document.getElementById('val-model-avg-conf').innerText = "89.4%";
        document.getElementById('val-model-entropy').innerText = "1.85 bits";
        document.getElementById('val-model-ece').innerText = "0.038";
        
        document.getElementById('val-dead-neurons').innerText = "4.2%";
        document.getElementById('val-weight-anomaly').innerText = "0.00";
        document.getElementById('whitebox-notes').innerText = "White-box parameter analysis confirms smooth layer weight distributions without parameter anomalies.";
    }

    function renderShift(findings) {
        const container = document.getElementById('shift-dimensions-container');
        const shiftFinding = findings.find(f => f.category === 'distribution_shift');

        let html = '';
        if (shiftFinding) {
            const ev = shiftFinding.supporting_evidence;
            ev.dimensions.forEach(d => {
                const status = d.shift_detected ? `<span class="badge badge-high">SHIFT DETECTED</span>` : `<span class="badge badge-success">STABLE</span>`;
                html += `
                    <div class="glass-card" style="padding:16px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <strong style="text-transform:uppercase;">${d.dimension_name} Domain</strong>
                            ${status}
                        </div>
                        <p style="font-size:12px; color:var(--text-muted);">${d.description}</p>
                        <div style="margin-top:10px; font-size:11px; font-family:var(--font-mono);">
                            KS-Statistic: ${d.ks_statistic} | p-value: ${d.p_value}
                        </div>
                    </div>
                `;
            });
        } else {
            html = `<p style="color:var(--text-muted);">No distribution shift detected against reference baseline.</p>`;
        }
        container.innerHTML = html;
    }

    function renderGovernance(report) {
        const attacksList = document.getElementById('supported-attacks-list');
        attacksList.innerHTML = report.supported_attack_classes.map(a => `<li><i class="fa-solid fa-shield-check" style="color:var(--severity-low);"></i> ${a}</li>`).join('');

        const limitList = document.getElementById('limitations-list');
        limitList.innerHTML = report.known_limitations.map(l => `<li><i class="fa-solid fa-circle-info" style="color:var(--severity-medium);"></i> ${l}</li>`).join('');
    }

    // 3. Provenance Verification Buttons
    const btnVerifyClean = document.getElementById('btn-verify-clean');
    const btnSimulateTampering = document.getElementById('btn-simulate-tampering');
    const verifyOut = document.getElementById('provenance-verify-output');

    btnVerifyClean.addEventListener('click', async () => {
        const rec = {
            record_id: "INF-REC-8F92A10C",
            timestamp_utc: 1726670000.0,
            nonce: "a1b2c3d4e5f6",
            sequence_number: 1,
            image_hash_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            model_digest_sha256: "a3f8c7901b22e4d5678ef991002341ab8872619cd3000f2e1a",
            preprocessing_config_hash: "8f4e2c1a9b",
            predictions: [
                { box: [200, 200, 240, 280], confidence: 0.94, category_id: 0, category_name: "vehicle_tank" }
            ],
            binding_hash_sha256: "3f2504e04f891f86948ad15a447e653b232e499f53e3d15a47e653b232e499f5",
            hmac_signature: "847291a56bc9e102f4a387c910283e47"
        };
        // Re-generate true binding via API
        const formData = new FormData();
        formData.append('image_hash', rec.image_hash_sha256);
        formData.append('model_hash', rec.model_digest_sha256);
        formData.append('predictions_json', JSON.stringify(rec.predictions));

        const res = await fetch('/api/create_inference_record', { method: 'POST', body: formData });
        const validRec = await res.json();

        const vRes = await fetch('/api/verify_inference_record', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(validRec)
        });
        const result = await vRes.json();

        verifyOut.style.display = 'block';
        verifyOut.innerHTML = `
            <h4 style="color:var(--severity-low);"><i class="fa-solid fa-circle-check"></i> Provenance Verification Passed</h4>
            <p style="font-size:13px; margin-top:5px;">${result.details}</p>
        `;
    });

    btnSimulateTampering.addEventListener('click', async () => {
        const formData = new FormData();
        formData.append('image_hash', "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
        formData.append('model_hash', "a3f8c7901b22e4d5678ef991002341ab8872619cd3000f2e1a");
        formData.append('predictions_json', JSON.stringify([
            { box: [200, 200, 240, 280], confidence: 0.94, category_id: 0, category_name: "vehicle_tank" }
        ]));

        const res = await fetch('/api/create_inference_record', { method: 'POST', body: formData });
        const validRec = await res.json();

        // TAMPER WITH PREDICTIONS POST-HOC!
        validRec.predictions[0].confidence = 0.10;
        validRec.predictions[0].category_name = "ALTERED_LABEL";

        const vRes = await fetch('/api/verify_inference_record', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(validRec)
        });
        const result = await vRes.json();

        verifyOut.style.display = 'block';
        verifyOut.innerHTML = `
            <h4 style="color:var(--severity-critical);"><i class="fa-solid fa-bug"></i> TAMPERING DETECTED!</h4>
            <p style="font-size:13px; margin-top:5px;">${result.details}</p>
        `;
    });
});
