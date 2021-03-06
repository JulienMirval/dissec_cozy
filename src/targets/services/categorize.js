global.fetch = require('node-fetch').default

import fs from 'fs'
import CozyClient, { Q } from 'cozy-client'
import { BANK_DOCTYPE } from '../../doctypes'
import { Model } from './model'
import dissecConfig from '../../../dissec.config.json'
import { JOBS_DOCTYPE } from '../../doctypes/jobs'

export const categorize = async () => {
  const client = CozyClient.fromEnv(process.env, {})

  // Fetching parameters (if any) from the jobs
  const { data: job } = await client.query(Q(JOBS_DOCTYPE).getById(process.env['COZY_JOB_ID'].split('/')[2]))

  const { pretrained, filters = {} } = job.attributes.message

  // Fetch data
  const { data: operations } = await client.query(Q(BANK_DOCTYPE))

  // Fetch model or initialize it
  let model
  if (pretrained) {
    // Use the shared model
    try {
      const compressedAggregate = fs.readFileSync(dissecConfig.localModelPath).toString()
      model = await Model.fromCompressedAggregate(compressedAggregate)
    } catch (err) {
      throw `Model does not exist at path ${dissecConfig.localModelPath} ? ${err}`
    }
  } else {
    // Apply filters first
    let filteredOperations = filters.minOperationDate
      ? operations.filter(e => new Date(e.date).valueOf() <= new Date(filters.minOperationDate).valueOf())
      : operations

    model = await Model.fromDocs(filteredOperations)
  }

  // Categorize each doc and update it
  const categorized = operations.map(operation => {
    const prediction = model.predict(operation.label)
    return {
      ...operation,
      automaticCategoryId: prediction
    }
  })
  await client.saveAll(categorized)
}

categorize().catch(e => {
  // eslint-disable-next-line no-console
  console.log('critical', e)
  process.exit(1)
})
