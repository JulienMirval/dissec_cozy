global.fetch = require('node-fetch').default

import fs from 'fs'
import CozyClient, { Q } from 'cozy-client'
import { BANK_DOCTYPE } from '../../doctypes'
import { createLogger, getAppDirectory } from './helpers'
import { Model } from './model'
import dissecConfig from '../../../dissec.config.json'

export const contribution = async () => {
  const { parents, nbShares, pretrained, executionId, filters = {} } = JSON.parse(process.env['COZY_PAYLOAD'] || '{}')

  if (parents.length !== nbShares) {
    return
  }

  const client = CozyClient.fromEnv(process.env, {})

  const log = createLogger(client.stackClient.uri)

  const selector = filters.minOperationDate
    ? {
        date: { $lte: filters.minOperationDate }
      }
    : {}

  // Fetch training data
  const { data: operations } = await client.query(
    Q(BANK_DOCTYPE)
      .where(selector)
      .sortBy([{ date: 'asc' }])
  )

  // Fetch model
  let model
  if (pretrained) {
    try {
      let backup = fs.readFileSync(dissecConfig.localModelPath)
      model = Model.fromBackup(backup)

      model.train(operations)
    } catch (e) {
      throw `Model does not exist at path ${dissecConfig.localModelPath}`
    }
  } else {
    model = await Model.fromDocs(operations)
  }

  const appDirectory = await getAppDirectory(client)

  // Create a directory specifically for this aggregation
  // This prevents mixing shares from different execution
  const { data: aggregationDirectoryDoc } = await client
    .collection('io.cozy.files')
    .getDirectoryOrCreate(executionId, appDirectory)
  const aggregationDirectoryId = aggregationDirectoryDoc._id

  // Split model in shares
  let shares = model.getCompressedShares(nbShares)

  // Create a file for each share
  const files = []
  for (let i in shares) {
    const { data: file } = await client.create('io.cozy.files', {
      type: 'file',
      name: `contribution_${i}`,
      dirId: aggregationDirectoryId,
      data: shares[i]
    })
    files.push(file._id)
  }

  // Create sharing permissions for shares
  const shareCodes = []
  for (let i in files) {
    const { data: sharing } = await client.create('io.cozy.permissions', {
      codes: `aggregator${i}`,
      ttl: '1h',
      permissions: {
        shares: {
          type: 'io.cozy.files',
          verbs: ['GET', 'POST'],
          values: [files[i]]
        }
      }
    })
    shareCodes.push(sharing.attributes.shortcodes[`aggregator${i}`])
  }

  // Call webhooks of parents with the share
  for (let i in shareCodes) {
    // HACK: Using a delay to give enough time to the responding service to store shares
    await new Promise(resolve => setTimeout(resolve, 5000))
    // TODO: Launch the webhook without using fetchJSON
    await client.stackClient.fetchJSON('POST', parents[i].webhook, {
      executionId,
      docId: files[i],
      sharecode: shareCodes[i],
      uri: client.stackClient.uri,
      nbShares,
      parent: parents[i].parent,
      finalize: parents[i].finalize,
      level: parents[i].level,
      aggregatorId: parents[i].aggregatorId,
      nbChild: parents[i].nbChild
    })
    log(`Sent share ${Number(i) + 1} to aggregator ${parents[i].webhook}`)
  }
}

contribution().catch(e => {
  // eslint-disable-next-line no-console
  console.log('critical', e)
  process.exit(1)
})
