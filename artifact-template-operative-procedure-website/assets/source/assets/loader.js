(async () => {
    'use strict';
    const { anatomyChunks, manifestUrl, meshCount } = document.currentScript.dataset;
    const chunkCount = Number(anatomyChunks);
    const loadingId = manifestUrl ? 'anatomy-loading' : 'guide-loading';
    const message = document.getElementById(loadingId + '-message');
    const request = new AbortController();
    const { signal } = request;
    try {
        if (typeof DecompressionStream === 'undefined')
            throw new Error('Please open this guide in a current version of Chrome, Edge, Firefox or Safari.');

        // The files are consecutive pieces of one gzip stream.
        const decoder = new DecompressionStream('gzip');
        const load = async () => {
            try {
                for (let index = 1; index <= chunkCount; index++) {
                    const name = 'assets/anatomy-' + String(index).padStart(2, '0') + '.bin';
                    const response = await fetch(name, { signal });
                    if (!response.ok)
                        throw new Error('Anatomy data could not be loaded (' + response.status + ').');
                    await response.body.pipeTo(decoder.writable, { preventClose: true, signal });
                    if (!signal.aborted)
                        message.textContent = 'Loading Anatomy… ' + Math.round(index / chunkCount * 100) + '%';
                }
                await decoder.writable.close();
            } catch (error) {
                await decoder.writable.abort(error);
                throw error;
            }
        };
        const manifestRequest = manifestUrl
            ? fetch(manifestUrl, { signal }).then(response => {
                if (!response.ok)
                    throw new Error('The anatomy manifest could not be loaded.');
                return response.json();
            }) : null;
        const [data, manifest] = await Promise.all([
            new Response(decoder.readable).json(), manifestRequest, load()
        ]);
        // The retained reference serves its manifest separately.
        const payload = manifestUrl ? { 'manifest-data': manifest, 'mesh-data': data } : data;
        const expectedCount = manifestUrl ? manifest.structure_count : Number(meshCount);
        if (!Array.isArray(payload['mesh-data']) || payload['mesh-data'].length !== expectedCount)
            throw new Error('Anatomy data is incomplete. Please refresh the page.');
        window.__GUIDE_DATA__ = payload;
        const script = document.createElement('script');
        script.src = 'assets/app.js';
        script.onload = () => document.getElementById(loadingId)?.remove();
        script.onerror = () => { message.textContent = 'The guide could not be loaded. Please refresh the page.'; };
        document.body.append(script);
    }
    catch (error) {
        request.abort();
        message.textContent = error.message || 'Anatomy could not be loaded. Please refresh the page.';
        console.error(error);
    }
})();
