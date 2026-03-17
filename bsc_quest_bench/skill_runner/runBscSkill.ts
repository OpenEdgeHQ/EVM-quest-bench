/**
 * BSC Skill Runner
 * 
 * Executes LLM-generated TypeScript code and returns transaction objects.
 * 
 * Usage:
 *   bun runBscSkill.ts <code_file> <provider_url> <agent_address> <contracts_json> <timeout_ms>
 */

import { readFileSync } from 'fs';
import { pathToFileURL } from 'url';

interface SkillModule {
    executeSkill: (
        providerUrl: string,
        agentAddress: string,
        deployedContracts: Record<string, string>
    ) => Promise<Record<string, any>>;
}

async function runSkill() {
    // Parse command line arguments
    const args = process.argv.slice(2);
    
    if (args.length < 5) {
        console.error(JSON.stringify({
            success: false,
            error: 'Usage: runBscSkill.ts <code_file> <provider_url> <agent_address> <contracts_json> <timeout_ms>'
        }));
        process.exit(1);
    }
    
    const [codeFile, providerUrl, agentAddress, contractsJson, timeoutMs] = args;
    
    const timeout = parseInt(timeoutMs);
    
    console.error('🔍 [DEBUG] Starting runBscSkill');
    console.error(`🔍 [DEBUG] Code file: ${codeFile}`);
    console.error(`🔍 [DEBUG] Provider URL: ${providerUrl}`);
    console.error(`🔍 [DEBUG] Agent address: ${agentAddress}`);
    console.error(`🔍 [DEBUG] Timeout: ${timeout}ms`);
    
    try {
        // Parse deployed contracts
        const deployedContracts: Record<string, string> = JSON.parse(contractsJson);
        console.error('🔍 [DEBUG] Deployed contracts parsed successfully');
        
        // Import the skill module
        // Convert file path to file:// URL for dynamic import
        const moduleUrl = pathToFileURL(codeFile).href;
        console.error(`🔍 [DEBUG] Module URL: ${moduleUrl}`);
        
        // Execute with timeout
        console.error('🔍 [DEBUG] Starting execution with timeout...');
        const startTime = Date.now();
        
        let txObject = await Promise.race([
            (async () => {
                try {
                    console.error('🔍 [DEBUG] Step 1: Dynamic import starting...');
                    const importStart = Date.now();
                    const skillModule = await import(moduleUrl) as SkillModule;
                    const importTime = Date.now() - importStart;
                    console.error(`🔍 [DEBUG] Step 1: Dynamic import completed (${importTime}ms)`);
                    
                    // Check if executeSkill function exists
                    if (typeof skillModule.executeSkill !== 'function') {
                        throw new Error('executeSkill function not found in module. Make sure to export: export async function executeSkill(...)');
                    }
                    console.error('🔍 [DEBUG] Step 2: executeSkill function found');
                    
                    // Execute the skill
                    console.error('🔍 [DEBUG] Step 3: Calling executeSkill...');
                    const execStart = Date.now();
                    const result = await skillModule.executeSkill(
                        providerUrl,
                        agentAddress,
                        deployedContracts
                    );
                    const execTime = Date.now() - execStart;
                    console.error(`🔍 [DEBUG] Step 3: executeSkill completed (${execTime}ms)`);
                    
                    return result;
                } catch (error: any) {
                    console.error(`🔍 [DEBUG] Error in execution: ${error.message}`);
                    throw error;
                }
            })(),
            new Promise<never>((_, reject) => {
                setTimeout(() => {
                    const elapsed = Date.now() - startTime;
                    console.error(`🔍 [DEBUG] TIMEOUT: Execution exceeded ${timeout}ms (elapsed: ${elapsed}ms)`);
                    reject(new Error(`Execution timeout after ${timeout}ms`));
                }, timeout);
            })
        ]);
        
        const totalTime = Date.now() - startTime;
        console.error(`🔍 [DEBUG] Total execution time: ${totalTime}ms`);
        
        // 🔧 Parse JSON string if needed (support both string and object returns)
        if (typeof txObject === 'string') {
            try {
                txObject = JSON.parse(txObject);
            } catch (parseError: any) {
                throw new Error(`Failed to parse transaction JSON string: ${parseError.message}`);
            }
        }
        
        // Ensure txObject is an object
        if (typeof txObject !== 'object' || txObject === null) {
            throw new Error(`executeSkill must return a transaction object or JSON string, got: ${typeof txObject}`);
        }
        
        // Check if this is a query operation (returns query_result instead of transaction)
        if ('query_result' in txObject) {
            console.error('🔍 DEBUG - Query operation detected, returning result directly');
            
            // Return query result directly (no transaction serialization needed)
            console.log(JSON.stringify({
                success: true,
                tx_object: txObject,  // Contains query_result
                execution_time: Date.now()
            }, (key, value) =>
                typeof value === 'bigint' ? value.toString() : value
            ));
            
            process.exit(0);
        }
        
        // Check if this is a query result (not a transaction)
        if (txObject.type === 'QUERY_RESULT') {
            console.error('🔍 DEBUG - Query Result (not a transaction):');
            console.error(JSON.stringify(txObject, (key, value) =>
                typeof value === 'bigint' ? value.toString() : value
            , 2));
            
            // Return success with query result directly
            console.log(JSON.stringify({
                success: true,
                is_query: true,
                execution_time: Date.now(),
                tx_object: txObject
            }, (key, value) =>
                typeof value === 'bigint' ? value.toString() : value
            ));
            
            process.exit(0);
        }
        
        // Check if this looks like a query result with balances (no 'to' field, has 'balances' or 'success')
        if (txObject.balances || (txObject.success === true && !('to' in txObject) && !('data' in txObject))) {
            console.error('🔍 DEBUG - Query Result with balances detected:');
            console.error(JSON.stringify(txObject, (key, value) =>
                typeof value === 'bigint' ? value.toString() : value
            , 2));
            
            // Return success with query result directly
            console.log(JSON.stringify({
                success: true,
                is_query: true,
                execution_time: Date.now(),
                tx_object: {
                    type: 'QUERY_RESULT',
                    ...txObject
                }
            }, (key, value) =>
                typeof value === 'bigint' ? value.toString() : value
            ));
            
            process.exit(0);
        }
        
        // Validate transaction object has required fields
        const requiredFields = ['to'];
        const missingFields = requiredFields.filter(field => !(field in txObject));
        
        if (missingFields.length > 0) {
            console.warn(`Warning: Transaction missing recommended fields: ${missingFields.join(', ')}`);
        }
        
        // Serialize transaction to bytes using ethers
        const { ethers } = await import('ethers');
        
        // Debug: Print transaction object before serialization
        console.error('🔍 DEBUG - Transaction Object:');
        console.error(JSON.stringify(txObject, (key, value) =>
            typeof value === 'bigint' ? value.toString() : value
        , 2));
        
        // Remove 'from' field before serialization (unsigned transactions don't have 'from')
        const { from, ...txWithoutFrom } = txObject;
        
        console.error('🔍 DEBUG - Transaction Object (without from):');
        console.error(JSON.stringify(txWithoutFrom, (key, value) =>
            typeof value === 'bigint' ? value.toString() : value
        , 2));
        
        const serializedTx = ethers.Transaction.from(txWithoutFrom).unsignedSerialized;
        
        // Convert to base64
        const serializedTxBase64 = Buffer.from(serializedTx.slice(2), 'hex').toString('base64');
        
        // Return success with base64 encoded serialized transaction and tx object for debugging
        console.log(JSON.stringify({
            success: true,
            serialized_tx: serializedTxBase64,
            execution_time: Date.now(),
            tx_object: txObject  // Include for debugging (will be stringified)
        }, (key, value) =>
            typeof value === 'bigint' ? value.toString() : value
        ));
        
        process.exit(0);
        
    } catch (error: any) {
        // Return error
        console.log(JSON.stringify({
            success: false,
            error: error.message || String(error),
            stack: error.stack,
            execution_time: Date.now()
        }, (key, value) =>
            typeof value === 'bigint' ? value.toString() : value
        ));
        
        process.exit(1);
    }
}

// Run the skill
runSkill().catch((error) => {
    console.error(JSON.stringify({
        success: false,
        error: `Fatal error: ${error.message}`,
        stack: error.stack
    }, (key, value) =>
        typeof value === 'bigint' ? value.toString() : value
    ));
    process.exit(1);
});

