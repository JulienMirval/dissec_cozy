import { NodeRole } from '../node'
import NodesManager from '../manager'
import { Message, MessageType } from '../message'
import TreeNode from '../treeNode'

describe('Send aggregate', () => {
  const config = {
    averageLatency: 100,
    maxToAverageRatio: 10,
    averageCryptoTime: 100,
    averageComputeTime: 100,
    healthCheckPeriod: 3,
    multicastSize: 5,
    deadline: 100000,
    failureRate: 0.0004,
    depth: 3,
    fanout: 4,
    groupSize: 3,
    seed: '4-7'
  }

  let root: TreeNode
  let manager: NodesManager

  beforeEach(() => {
    const { node } = TreeNode.createTree(config.depth, config.fanout, config.groupSize, 0)
    root = node
    manager = NodesManager.createFromTree(root, config)
  })

  it('should make the querier add the aggregate to its buffer and finalize the computation if possible', async () => {
    const receptionTime = 10
    const agg1 = { data: 42, counter: 1, id: '1' }
    const treenode = root.children[0]
    const node = manager.nodes[root.id]
    node.role = NodeRole.Querier

    let messages = node.receiveMessage(
      new Message(MessageType.SendAggregate, 0, receptionTime, treenode.id, root.id, { aggregate: agg1 })
    )

    expect(node.aggregates[treenode.id]).toStrictEqual(agg1)
    expect(node.finishedWorking).toBeFalsy()
    expect(messages.length).toBe(0)

    messages = node.receiveMessage(
      new Message(MessageType.SendAggregate, 0, receptionTime, root.children[0].members[1], root.id, {
        aggregate: agg1
      })
    )

    expect(node.aggregates[root.children[0].members[1]]).toStrictEqual(agg1)
    expect(node.finishedWorking).toBeFalsy()
    expect(messages.length).toBe(0)

    messages = node.receiveMessage(
      new Message(MessageType.SendAggregate, 0, receptionTime, root.children[0].members[2], root.id, {
        aggregate: agg1
      })
    )

    expect(node.aggregates[root.children[0].members[2]]).toStrictEqual(agg1)
    expect(node.finishedWorking).toBeTruthy()
    expect(messages.length).toBe(1)
  })

  it('should fail when the node does not know the tree', async () => {
    const receptionTime = 10
    const treenode = root.children[0]
    const message = new Message(MessageType.SendAggregate, 0, receptionTime, root.id, treenode.id, {
      aggregate: { data: 0, counter: 1, id: '1' }
    })
    const node = manager.nodes[treenode.id]
    node.node = undefined
    expect(() => node.receiveMessage(message)).toThrow()
  })

  it('should fail when the node does not receive the aggregate', async () => {
    const receptionTime = 10
    const treenode = root.children[0]
    const message = new Message(MessageType.SendAggregate, 0, receptionTime, root.id, treenode.id, {})
    const node = manager.nodes[treenode.id]
    expect(() => node.receiveMessage(message)).toThrow()
  })
})
